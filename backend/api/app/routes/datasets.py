import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request

from ..auth import require_authentication
from ..aws import create_upload_url, delete_prefix
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
        response["headers"] = dataset.get("headers", [])
        response["rows"] = dataset.get("previewRows", [])
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
    get_store().put_dataset(dataset)
    return jsonify({"dataset": serialize_dataset(dataset), "upload": create_upload_url(current_app.config["UPLOAD_BUCKET"], s3_key, content_type)}), 201


@datasets_blueprint.get("/<dataset_id>")
@require_authentication
def get_dataset(dataset_id):
    return jsonify(serialize_dataset(require_owned_dataset(dataset_id), include_preview=True))


@datasets_blueprint.delete("/<dataset_id>")
@require_authentication
def delete_dataset(dataset_id):
    dataset = require_owned_dataset(dataset_id)
    prefix = f"datasets/{g.current_user['userId']}/{dataset_id}/"
    delete_prefix(current_app.config["UPLOAD_BUCKET"], prefix)
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
    rows = dataset.get("previewRows", [])
    if column not in headers:
        raise ApiError("Select a valid dataset column.", 400, "INVALID_COLUMN")
    if operator not in {"contains", "equals", "greater", "less", "empty"}:
        raise ApiError("Select a valid query operator.", 400, "INVALID_OPERATOR")
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
    return jsonify({"headers": headers, "rows": matched_rows[:100], "count": len(matched_rows)})
