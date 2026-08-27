import os
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3


REGION = os.getenv("AWS_REGION", "us-east-1")
ecs = boto3.client("ecs", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)


def handler(event, _context):
    table = dynamodb.Table(os.environ["DATASETS_TABLE"])
    started = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        parts = key.split("/")
        if len(parts) < 4 or parts[0] != "datasets" or parts[-1] == "preview.json":
            continue
        user_id, dataset_id = parts[1], parts[2]
        table.update_item(
            Key={"userId": user_id, "datasetId": dataset_id},
            UpdateExpression="SET #status = :processing, updatedAt = :updated",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":processing": "processing", ":updated": datetime.now(timezone.utc).isoformat()},
        )
        response = ecs.run_task(
            cluster=os.environ["ECS_CLUSTER"],
            taskDefinition=os.environ["PROCESSOR_TASK_DEFINITION"],
            launchType="FARGATE",
            count=1,
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": os.environ["ECS_SUBNETS"].split(","),
                    "securityGroups": [os.environ["ECS_SECURITY_GROUP"]],
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": "csv-processor",
                        "environment": [
                            {"name": "USER_ID", "value": user_id},
                            {"name": "DATASET_ID", "value": dataset_id},
                            {"name": "S3_BUCKET", "value": bucket},
                            {"name": "S3_KEY", "value": key},
                        ],
                    }
                ]
            },
        )
        if response.get("failures"):
            raise RuntimeError(f"ECS task failed to start: {response['failures']}")
        started.extend(task["taskArn"] for task in response.get("tasks", []))
    return {"startedTasks": started}
