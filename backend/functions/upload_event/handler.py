import os
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError


REGION = os.getenv("AWS_REGION", "us-east-1")


def transition(table, key, expected, status, **extra):
    values = {":expected": expected, ":status": status, ":updated": datetime.now(timezone.utc).isoformat()}
    names = {"#status": "status"}
    assignments = ["#status = :status", "updatedAt = :updated"]
    for index, (name, value) in enumerate(extra.items()):
        names[f"#f{index}"] = name
        values[f":v{index}"] = value
        assignments.append(f"#f{index} = :v{index}")
    try:
        table.update_item(
            Key=key, UpdateExpression="SET " + ", ".join(assignments),
            ConditionExpression="attribute_exists(datasetId) AND #status = :expected",
            ExpressionAttributeNames=names, ExpressionAttributeValues=values,
        )
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def handle_stopped_task(table, event):
    detail = event.get("detail", {})
    if detail.get("lastStatus") != "STOPPED":
        return {"failedTasks": 0}
    for container in detail.get("overrides", {}).get("containerOverrides", []):
        if container.get("name") != "csv-processor":
            continue
        env = {item["name"]: item["value"] for item in container.get("environment", [])}
        if not env.get("USER_ID") or not env.get("DATASET_ID"):
            continue
        key = {"userId": env["USER_ID"], "datasetId": env["DATASET_ID"]}
        reason = detail.get("stoppedReason", "Processor stopped before completing the dataset.")[:500]
        for status in ("dispatching", "processing"):
            if transition(table, key, status, "failed", errorMessage=reason):
                return {"failedTasks": 1}
    return {"failedTasks": 0}


def handler(event, _context):
    table = boto3.resource("dynamodb", region_name=REGION).Table(os.environ["DATASETS_TABLE"])
    if event.get("source") == "aws.ecs":
        return handle_stopped_task(table, event)
    if event.get("requestContext", {}).get("condition") in {"RetriesExhausted", "EventAgeExceeded"}:
        failed = 0
        for record in event.get("requestPayload", {}).get("Records", []):
            parts = unquote_plus(record["s3"]["object"]["key"]).split("/")
            if len(parts) == 4 and parts[0] == "datasets" and parts[3] == "source.csv":
                key = {"userId": parts[1], "datasetId": parts[2]}
                failed += transition(table, key, "dispatching", "failed", errorMessage="Processor launch retries were exhausted. Upload the file again.")
        return {"failedTasks": failed}
    ecs = boto3.client("ecs", region_name=REGION)
    started = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        source_key = unquote_plus(record["s3"]["object"]["key"])
        parts = source_key.split("/")
        if len(parts) != 4 or parts[0] != "datasets" or parts[3] != "source.csv":
            continue
        user_id, dataset_id = parts[1], parts[2]
        key = {"userId": user_id, "datasetId": dataset_id}
        item = table.get_item(Key=key, ConsistentRead=True).get("Item")
        if not item or item.get("s3Key") != source_key or item["status"] not in {"uploading", "dispatching"}:
            continue
        if item["status"] == "uploading":
            if not transition(table, key, "uploading", "dispatching"):
                continue
        # Stable parameters and token let retries recover an uncertain RunTask response.
        # The worker also claims processing atomically before doing any work.
        # [3] Amazon Web Services, "Ensuring idempotency," Amazon ECS Developer Guide.
        # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html (accessed Sep. 5, 2026).
        response = ecs.run_task(
            clientToken=dataset_id,
            cluster=os.environ["ECS_CLUSTER"],
            taskDefinition=os.environ["PROCESSOR_TASK_DEFINITION"],
            launchType="FARGATE", count=1,
            networkConfiguration={"awsvpcConfiguration": {
                "subnets": [value.strip() for value in os.environ["ECS_SUBNETS"].split(",")],
                "securityGroups": [os.environ["ECS_SECURITY_GROUP"]], "assignPublicIp": "ENABLED",
            }},
            overrides={"containerOverrides": [{"name": "csv-processor", "environment": [
                {"name": "USER_ID", "value": user_id},
                {"name": "DATASET_ID", "value": dataset_id},
                {"name": "S3_BUCKET", "value": bucket},
                {"name": "S3_KEY", "value": source_key},
            ]}]},
        )
        if response.get("failures") or not response.get("tasks"):
            transition(table, key, "dispatching", "failed", errorMessage="ECS could not start the processor. Upload the file again.")
            continue
        started.extend(task["taskArn"] for task in response["tasks"])
    return {"startedTasks": started}
