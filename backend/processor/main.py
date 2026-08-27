import csv
import io
import json
import os
from datetime import datetime, timezone

import boto3


REGION = os.getenv("AWS_REGION", "us-east-1")


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
    table = boto3.resource("dynamodb", region_name=REGION).Table(os.environ["DATASETS_TABLE"])
    try:
        source = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        headers, rows, stats = analyze_csv(source)
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
