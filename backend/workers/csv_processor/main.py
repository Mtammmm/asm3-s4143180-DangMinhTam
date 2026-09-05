import csv
import io
import json
import os
import re
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


REGION = os.getenv("AWS_REGION", "us-east-1")
ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "csv_insight")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_COLUMNS = 500
MAX_HEADER_LENGTH = 200


def detect_dialect(text):
    sample = text[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def analyze_csv(content):
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text), dialect=detect_dialect(text), strict=True)
    try:
        records = [row for row in reader if any(cell.strip() for cell in row)]
    except csv.Error as error:
        raise ValueError(f"Invalid CSV: {error}") from error
    if len(records) < 2:
        raise ValueError("The CSV must contain a header and at least one data row.")
    if len(records[0]) > MAX_COLUMNS:
        raise ValueError(f"CSV files support at most {MAX_COLUMNS} columns.")
    headers = []
    used = set()
    for index, raw in enumerate(records[0]):
        base = raw.strip() or f"Column {index + 1}"
        if len(base) > MAX_HEADER_LENGTH:
            raise ValueError(f"Column names must not exceed {MAX_HEADER_LENGTH} characters.")
        name, suffix = base, 2
        while name in used:
            name = f"{base} ({suffix})"
            suffix += 1
        used.add(name)
        headers.append(name)
    if any(len(row) > len(headers) for row in records[1:]):
        raise ValueError("A CSV row contains more values than the header.")
    rows = [[row[index].strip() if index < len(row) else "" for index in range(len(headers))] for row in records[1:]]
    total_cells = len(headers) * len(rows)
    missing_values = sum(1 for row in rows for value in row if value == "")
    stats = {
        "rows": len(rows),
        "columns": len(headers),
        "missingValues": missing_values,
        "completeness": round(((total_cells - missing_values) / total_cells) * 100) if total_cells else 0,
    }
    return headers, rows, stats


def canonical_json_lines(columns, rows):
    # [1] Amazon Web Services, "Hive JSON SerDe," Amazon Athena User Guide.
    # https://docs.aws.amazon.com/athena/latest/ug/hive-json-serde.html (accessed Sep. 5, 2026).
    names = [column["name"] for column in columns]
    return "".join(json.dumps(dict(zip(names, row)), ensure_ascii=False) + "\n" for row in rows).encode("utf-8")


def athena_columns(headers):
    result = []
    used = set()
    for index, source in enumerate(headers):
        name = re.sub(r"[^a-z0-9_]", "_", source.lower()).strip("_")
        if not name or name[0].isdigit():
            name = f"column_{index + 1}_{name}".rstrip("_")
        name = name[:240]
        candidate = name
        suffix = 2
        while candidate in used:
            candidate = f"{name[:235]}_{suffix}"
            suffix += 1
        used.add(candidate)
        result.append({"source": source, "name": candidate})
    return result


def register_glue_table(glue, bucket, location_key, dataset_id, columns):
    table_name = "dataset_" + dataset_id.lower().replace("-", "_")
    try:
        glue.create_database(DatabaseInput={"Name": ATHENA_DATABASE, "Description": "CSV Insight datasets"})
    except glue.exceptions.AlreadyExistsException:
        pass
    table_input = {
        "Name": table_name,
        "Description": f"CSV Insight dataset {dataset_id}",
        "TableType": "EXTERNAL_TABLE",
        "Parameters": {"classification": "json"},
        "StorageDescriptor": {
            "Columns": [{"Name": item["name"], "Type": "string"} for item in columns],
            "Location": f"s3://{bucket}/{location_key}",
            "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.apache.hive.hcatalog.data.JsonSerDe",
            },
        },
    }
    try:
        glue.create_table(DatabaseName=ATHENA_DATABASE, TableInput=table_input)
    except glue.exceptions.AlreadyExistsException:
        glue.update_table(DatabaseName=ATHENA_DATABASE, TableInput=table_input)
    return table_name


def update_dataset(table, user_id, dataset_id, values, expected_status="processing"):
    names = {f"#field{index}": key for index, key in enumerate(values)}
    attributes = {f":value{index}": value for index, value in enumerate(values.values())}
    assignments = ", ".join(f"{name} = {value}" for name, value in zip(names, attributes))
    names["#expectedStatus"] = "status"
    attributes[":expectedStatus"] = expected_status
    try:
        table.update_item(
            Key={"userId": user_id, "datasetId": dataset_id},
            UpdateExpression=f"SET {assignments}",
            ConditionExpression="attribute_exists(datasetId) AND #expectedStatus = :expectedStatus",
            ExpressionAttributeNames=names, ExpressionAttributeValues=attributes,
        )
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def run():
    user_id = os.environ["USER_ID"]
    dataset_id = os.environ["DATASET_ID"]
    bucket = os.environ["S3_BUCKET"]
    key = os.environ["S3_KEY"]
    s3 = boto3.client("s3", region_name=REGION)
    glue = boto3.client("glue", region_name=REGION)
    table = boto3.resource("dynamodb", region_name=REGION).Table(os.environ["DATASETS_TABLE"])
    if not update_dataset(table, user_id, dataset_id, {
        "status": "processing", "updatedAt": datetime.now(timezone.utc).isoformat(),
    }, expected_status="dispatching"):
        return
    try:
        source_object = s3.get_object(Bucket=bucket, Key=key)
        try:
            if source_object["ContentLength"] > MAX_UPLOAD_BYTES:
                raise ValueError("CSV file exceeds the upload size limit.")
            source = source_object["Body"].read(MAX_UPLOAD_BYTES + 1)
            if len(source) > MAX_UPLOAD_BYTES:
                raise ValueError("CSV file exceeds the upload size limit.")
        finally:
            source_object["Body"].close()
        headers, rows, stats = analyze_csv(source)
        columns = athena_columns(headers)
        if len(json.dumps({"headers": headers, "columns": columns}, ensure_ascii=False).encode("utf-8")) > 200_000:
            raise ValueError("CSV column metadata is too large. Shorten the column names or reduce the column count.")
        athena_key = f"datasets/{user_id}/{dataset_id}/athena-v2/rows.jsonl"
        s3.put_object(Bucket=bucket, Key=athena_key, Body=canonical_json_lines(columns, rows), ContentType="application/x-ndjson")
        table_name = register_glue_table(
            glue, bucket, f"datasets/{user_id}/{dataset_id}/athena-v2/", dataset_id, columns
        )
        preview_key = f"datasets/{user_id}/{dataset_id}/preview.json"
        s3.put_object(
            Bucket=bucket,
            Key=preview_key,
            Body=json.dumps({"headers": headers, "rows": rows[:100]}, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        update_dataset(
            table,
            user_id,
            dataset_id,
            {
                "status": "ready",
                "stats": stats,
                "headers": headers,
                "previewKey": preview_key,
                "athenaDatabase": ATHENA_DATABASE,
                "athenaTable": table_name,
                "athenaColumns": columns,
                "athenaLocation": f"s3://{bucket}/datasets/{user_id}/{dataset_id}/athena-v2/",
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as error:
        update_dataset(
            table,
            user_id,
            dataset_id,
            {
                "status": "failed",
                "errorMessage": str(error)[:500],
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise


if __name__ == "__main__":
    run()
