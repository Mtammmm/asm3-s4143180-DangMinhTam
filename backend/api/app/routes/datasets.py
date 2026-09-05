import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request

from ..auth import require_authentication
from ..athena import run_query
from ..aws import create_dataset_upload, delete_glue_table, delete_prefix, read_preview
from ..errors import ApiError
from ..store import get_store


datasets_blueprint = Blueprint("datasets", __name__)


def serialize_dataset(dataset, include_preview=False):
    response = {
        "id": dataset["datasetId"],
        "name": dataset["fileName"],
        "size": dataset["fileSize"],
        "status": dataset["status"],
        "createdAt": dataset["createdAt"],
        "updatedAt": dataset["updatedAt"],
        "stats": dataset.get("stats"),
    }
    if include_preview:
        preview = read_preview(current_app.config["UPLOAD_BUCKET"], dataset["previewKey"]) if dataset.get("previewKey") and current_app.config["STORAGE_BACKEND"] == "aws" else {}
        response["headers"] = dataset.get("headers", [])
        response["rows"] = preview.get("rows", dataset.get("previewRows", []))
        response["errorMessage"] = dataset.get("errorMessage")
    return response


def require_owned_dataset(dataset_id):
    dataset = get_store().get_dataset(g.current_user["userId"], dataset_id)
    if not dataset:
        raise ApiError("Dataset was not found.", 404, "DATASET_NOT_FOUND")
    return dataset


@datasets_blueprint.get("")
@require_authentication
def list_datasets():
    search = request.args.get("search", "").strip().lower()
    status = request.args.get("status", "").strip().lower()
    datasets = get_store().list_datasets(g.current_user["userId"])
    if search:
        datasets = [dataset for dataset in datasets if search in dataset["fileName"].lower()]
    if status:
        datasets = [dataset for dataset in datasets if dataset["status"] == status]
    return jsonify([serialize_dataset(dataset) for dataset in datasets])


@datasets_blueprint.post("")
@require_authentication
def create_dataset():
    payload = request.get_json(silent=True) or {}
    file_name = str(payload.get("name", "")).strip()
    content_type = str(payload.get("contentType", "text/csv")).strip().lower()
    try:
        file_size = int(payload.get("size", 0))
    except (TypeError, ValueError) as error:
        raise ApiError("File size must be a number.", 400, "INVALID_FILE_SIZE") from error
    if not file_name.lower().endswith(".csv"):
        raise ApiError("Only CSV files are supported.", 400, "INVALID_FILE_TYPE")
    if file_size <= 0 or file_size > current_app.config["MAX_UPLOAD_BYTES"]:
        raise ApiError("CSV files must be between 1 byte and 10 MB.", 413, "INVALID_FILE_SIZE")
    if content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"}:
        raise ApiError("The supplied content type is not supported.", 400, "INVALID_CONTENT_TYPE")
    dataset_id = str(uuid.uuid4())
    s3_key = f"datasets/{g.current_user['userId']}/{dataset_id}/source.csv"
    now = datetime.now(timezone.utc).isoformat()
    dataset = {
        "userId": g.current_user["userId"],
        "datasetId": dataset_id,
        "fileName": file_name,
        "fileSize": file_size,
        "contentType": content_type,
        "s3Key": s3_key,
        "status": "uploading",
        "stats": None,
        "createdAt": now,
        "updatedAt": now,
    }
    if current_app.config["STORAGE_BACKEND"] == "memory":
        upload = {"url": f"{request.url_root.rstrip('/')}/datasets/{dataset_id}/content", "method": "PUT", "authenticated": True}
    else:
        upload = create_dataset_upload(current_app.config["UPLOAD_BUCKET"], s3_key, content_type, file_size)
    get_store().put_dataset(dataset)
    return jsonify({"dataset": serialize_dataset(dataset), "upload": upload}), 201


@datasets_blueprint.put("/<dataset_id>/content")
@require_authentication
def upload_local_dataset(dataset_id):
    if current_app.config["STORAGE_BACKEND"] != "memory":
        raise ApiError("Local uploads are unavailable in AWS mode.", 404, "NOT_FOUND")
    dataset = require_owned_dataset(dataset_id)
    if dataset["status"] != "uploading":
        raise ApiError("This dataset has already been uploaded.", 409, "UPLOAD_ALREADY_COMPLETED")
    content = request.get_data()
    if len(content) != dataset["fileSize"] or len(content) > current_app.config["MAX_UPLOAD_BYTES"]:
        raise ApiError("Uploaded size does not match the declared file size.", 413, "INVALID_FILE_SIZE")
    # The local runner adds backend/workers to sys.path; Lambda never imports this module.
    from csv_processor.main import analyze_csv
    try:
        headers, rows, stats = analyze_csv(content)
    except (ValueError, UnicodeError) as error:
        dataset.update(status="failed", errorMessage=str(error)[:500])
    else:
        dataset.update(status="ready", headers=headers, previewRows=rows[:100], localRows=rows, stats=stats)
    dataset["updatedAt"] = datetime.now(timezone.utc).isoformat()
    get_store().put_dataset(dataset)
    return jsonify(serialize_dataset(dataset, include_preview=True))


@datasets_blueprint.get("/<dataset_id>")
@require_authentication
def get_dataset(dataset_id):
    return jsonify(serialize_dataset(require_owned_dataset(dataset_id), include_preview=True))


@datasets_blueprint.delete("/<dataset_id>")
@require_authentication
def delete_dataset(dataset_id):
    dataset = require_owned_dataset(dataset_id)
    if not get_store().begin_delete_dataset(g.current_user["userId"], dataset_id):
        raise ApiError("Wait for dataset processing to finish before deleting it.", 409, "DATASET_BUSY")
    prefix = f"datasets/{g.current_user['userId']}/{dataset_id}/"
    delete_prefix(current_app.config["UPLOAD_BUCKET"], prefix)
    delete_glue_table(current_app.config["ATHENA_DATABASE"], dataset.get("athenaTable"))
    get_store().delete_dataset(g.current_user["userId"], dataset_id)
    return "", 204


@datasets_blueprint.post("/<dataset_id>/query")
@require_authentication
def query_dataset(dataset_id):
    dataset = require_owned_dataset(dataset_id)
    if dataset["status"] != "ready":
        raise ApiError("The dataset is not ready for queries.", 409, "DATASET_NOT_READY")
    payload = request.get_json(silent=True) or {}
    column = str(payload.get("column", ""))
    operator = str(payload.get("operator", "contains"))
    value = str(payload.get("value", ""))
    headers = dataset.get("headers", [])
    rows = dataset.get("localRows", dataset.get("previewRows", []))
    if column not in headers:
        raise ApiError("Select a valid dataset column.", 400, "INVALID_COLUMN")
    if operator not in {"contains", "equals", "greater", "less", "empty"}:
        raise ApiError("Select a valid query operator.", 400, "INVALID_OPERATOR")

    athena_columns = dataset.get("athenaColumns", [])
    athena_column = next((item["name"] for item in athena_columns if item["source"] == column), None)
    if dataset.get("athenaTable") and athena_column:
        rows, count = run_query(dataset["athenaTable"], athena_columns, athena_column, operator, value)
        return jsonify({"headers": headers, "rows": rows, "count": count, "queryEngine": "athena"})

    if dataset.get("previewKey") and current_app.config["STORAGE_BACKEND"] == "aws":
        rows = read_preview(current_app.config["UPLOAD_BUCKET"], dataset["previewKey"]).get("rows", [])

    # Datasets processed before Athena was enabled retain preview querying.
    index = headers.index(column)

    def matches(row):
        actual = str(row[index] if index < len(row) else "")
        if operator == "empty":
            return actual == ""
        if operator == "equals":
            return actual.casefold() == value.casefold()
        if operator in {"greater", "less"}:
            try:
                return float(actual) > float(value) if operator == "greater" else float(actual) < float(value)
            except ValueError:
                return False
        return value.casefold() in actual.casefold()

    matched_rows = [row for row in rows if matches(row)]
    return jsonify({"headers": headers, "rows": matched_rows[:100], "count": len(matched_rows), "queryEngine": "local" if "localRows" in dataset else "preview"})
