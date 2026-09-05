import csv
import io
import json
import os
import re
from datetime import datetime, timezone

import boto3


REGION = os.getenv("AWS_REGION", "us-east-1")
ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "csv_insight")


def detect_dialect(text):
    sample = text[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def analyze_csv(content):
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text), dialect=detect_dialect(text))
    records = [row for row in reader if any(cell.strip() for cell in row)]
    if len(records) < 2:
        raise ValueError("The CSV must contain a header and at least one data row.")
    headers = [header.strip() or f"Column {index + 1}" for index, header in enumerate(records[0])]
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


def register_glue_table(glue, bucket, location_key, dataset_id, columns, delimiter):
    table_name = "dataset_" + dataset_id.lower().replace("-", "_")
    try:
        glue.create_database(DatabaseInput={"Name": ATHENA_DATABASE, "Description": "CSV Insight datasets"})
    except glue.exceptions.AlreadyExistsException:
        pass
    table_input = {
        "Name": table_name,
        "Description": f"CSV Insight dataset {dataset_id}",
        "TableType": "EXTERNAL_TABLE",
        "Parameters": {"classification": "csv", "skip.header.line.count": "1"},
        "StorageDescriptor": {
            "Columns": [{"Name": item["name"], "Type": "string"} for item in columns],
            "Location": f"s3://{bucket}/{location_key}",
            "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.apache.hadoop.hive.serde2.OpenCSVSerde",
                "Parameters": {"separatorChar": delimiter, "quoteChar": '"', "escapeChar": "\\"},
            },
        },
    }
    try:
        glue.create_table(DatabaseName=ATHENA_DATABASE, TableInput=table_input)
    except glue.exceptions.AlreadyExistsException:
        glue.update_table(DatabaseName=ATHENA_DATABASE, TableInput=table_input)
    return table_name


def update_dataset(table, user_id, dataset_id, values):
    names = {f"#field{index}": key for index, key in enumerate(values)}
    attributes = {f":value{index}": value for index, value in enumerate(values.values())}
    assignments = ", ".join(f"{name} = {value}" for name, value in zip(names, attributes))
    table.update_item(
        Key={"userId": user_id, "datasetId": dataset_id},
        UpdateExpression=f"SET {assignments}",
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=attributes,
    )


def run():
    user_id = os.environ["USER_ID"]
    dataset_id = os.environ["DATASET_ID"]
    bucket = os.environ["S3_BUCKET"]
    key = os.environ["S3_KEY"]
    s3 = boto3.client("s3", region_name=REGION)
    glue = boto3.client("glue", region_name=REGION)
    table = boto3.resource("dynamodb", region_name=REGION).Table(os.environ["DATASETS_TABLE"])
    try:
        source = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        headers, rows, stats = analyze_csv(source)
        dialect = detect_dialect(source.decode("utf-8-sig"))
        columns = athena_columns(headers)
        athena_key = f"datasets/{user_id}/{dataset_id}/athena/source.data"
        s3.put_object(Bucket=bucket, Key=athena_key, Body=source, ContentType="text/csv")
        table_name = register_glue_table(
            glue, bucket, f"datasets/{user_id}/{dataset_id}/athena/", dataset_id, columns, dialect.delimiter
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
                "previewRows": rows[:100],
                "previewKey": preview_key,
                "athenaDatabase": ATHENA_DATABASE,
                "athenaTable": table_name,
                "athenaColumns": columns,
                "athenaLocation": f"s3://{bucket}/datasets/{user_id}/{dataset_id}/athena/",
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
