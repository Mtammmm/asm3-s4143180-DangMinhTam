import json
from unittest.mock import Mock

import boto3
import pytest
from moto import mock_aws

from app import create_app
from app.store import MemoryStore
from conftest import TestConfig
from csv_processor import main as processor
from functions.upload_event import handler as upload_event


def test_aws_refuses_default_secret_and_exposed_recovery_token():
    class CloudConfig(TestConfig):
        STORAGE_BACKEND = "aws"
        EXPOSE_RESET_TOKEN = False
        JWT_SECRET = ""

    with pytest.raises(ValueError, match="JWT_SECRET"):
        create_app(CloudConfig)
    CloudConfig.JWT_SECRET = "random-secret-for-aws-test-1234567890"
    CloudConfig.EXPOSE_RESET_TOKEN = True
    with pytest.raises(ValueError, match="EXPOSE_RESET_TOKEN"):
        create_app(CloudConfig)


def test_local_upload_query_and_delete_complete_flow(authenticated_client):
    content = b"name,value\n" + b"Alice,10\n" * 120
    result = authenticated_client.post("/datasets", json={"name": "data.csv", "size": len(content)}).get_json()
    dataset_id = result["dataset"]["id"]
    uploaded = authenticated_client.put(f"/datasets/{dataset_id}/content", data=content, content_type="text/csv")
    assert uploaded.status_code == 200
    assert uploaded.get_json()["stats"]["rows"] == 120
    assert len(uploaded.get_json()["rows"]) == 100
    query = authenticated_client.post(f"/datasets/{dataset_id}/query", json={"column": "name", "operator": "equals", "value": "Alice"})
    assert query.get_json()["count"] == 120
    assert len(query.get_json()["rows"]) == 100
    assert authenticated_client.delete(f"/datasets/{dataset_id}").status_code == 204


def test_processing_dataset_cannot_be_deleted(authenticated_client):
    result = authenticated_client.post("/datasets", json={"name": "data.csv", "size": 10}).get_json()
    key = next(iter(MemoryStore.datasets))
    MemoryStore.datasets[key]["status"] = "processing"
    assert authenticated_client.delete(f"/datasets/{result['dataset']['id']}").status_code == 409
    assert key in MemoryStore.datasets


def test_reset_code_is_single_use_and_private(authenticated_client):
    requested = authenticated_client.post("/auth/forgot-password", json={"email": "demo@csvinsight.com"}).get_json()
    profile = authenticated_client.get("/users/me").get_json()
    assert "resetTokenHash" not in profile
    assert "resetTokenExpiresAt" not in profile
    payload = {"email": "demo@csvinsight.com", "resetToken": requested["resetToken"], "newPassword": "NewPassword123"}
    assert authenticated_client.post("/auth/reset-password", json=payload).status_code == 200
    assert authenticated_client.post("/auth/reset-password", json=payload).status_code == 400


def test_ses_recovery_does_not_return_token(authenticated_client, app, monkeypatch):
    app.config.update(EXPOSE_RESET_TOKEN=False, RESET_EMAIL_SENDER="sender@example.com")
    send = Mock()
    monkeypatch.setattr("app.routes.auth.send_reset_email", send)
    result = authenticated_client.post("/auth/forgot-password", json={"email": "demo@csvinsight.com"})
    assert result.status_code == 200
    assert "resetToken" not in result.get_json()
    assert send.call_args.args[0] == "demo@csvinsight.com"
    assert len(send.call_args.args[1]) > 30


def test_canonical_data_preserves_normalized_preview():
    content = 'name,name,notes\n Alice , Bob ,"line 1\nline 2"\n,,\nEve,Fred,"a,b"\n'.encode()
    headers, rows, stats = processor.analyze_csv(content)
    assert headers == ["name", "name (2)", "notes"]
    columns = processor.athena_columns(headers)
    encoded = processor.canonical_json_lines(columns, rows)
    documents = [json.loads(line) for line in encoded.splitlines()]
    restored = [[record[column["name"]] for column in columns] for record in documents]
    assert restored == rows
    assert len(documents) == stats["rows"] == 2


@pytest.fixture
def cloud_pipeline(monkeypatch):
    with mock_aws():
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        for key, value in {
            "DATASETS_TABLE": "datasets", "ECS_CLUSTER": "cluster", "PROCESSOR_TASK_DEFINITION": "processor:1",
            "ECS_SUBNETS": "subnet-a", "ECS_SECURITY_GROUP": "sg-a", "USER_ID": "owner", "DATASET_ID": "dataset-1",
            "S3_BUCKET": "csv-test-bucket", "S3_KEY": "datasets/owner/dataset-1/source.csv",
        }.items():
            monkeypatch.setenv(key, value)
        table = boto3.resource("dynamodb", region_name="us-east-1").create_table(
            TableName="datasets", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "userId", "KeyType": "HASH"}, {"AttributeName": "datasetId", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "userId", "AttributeType": "S"}, {"AttributeName": "datasetId", "AttributeType": "S"}],
        )
        key = {"userId": "owner", "datasetId": "dataset-1"}
        table.put_item(Item={**key, "status": "uploading", "s3Key": "datasets/owner/dataset-1/source.csv"})
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="csv-test-bucket")
        s3.put_object(Bucket="csv-test-bucket", Key="datasets/owner/dataset-1/source.csv", Body=b"name,value\nAlice,10\n")
        ecs = Mock()
        ecs.run_task.return_value = {"tasks": [{"taskArn": "task-1"}]}
        real_client = boto3.client
        monkeypatch.setattr(boto3, "client", lambda service, **kwargs: ecs if service == "ecs" else real_client(service, **kwargs))
        event = {"Records": [{"s3": {"bucket": {"name": "csv-test-bucket"}, "object": {"key": "datasets/owner/dataset-1/source.csv"}}}]}
        yield table, key, s3, ecs, event


def test_s3_event_worker_and_glue_pipeline(cloud_pipeline):
    table, key, s3, ecs, event = cloud_pipeline
    assert upload_event.handler(event, None)["startedTasks"] == ["task-1"]
    assert table.get_item(Key=key)["Item"]["status"] == "dispatching"
    processor.run()
    item = table.get_item(Key=key)["Item"]
    assert item["status"] == "ready"
    assert item["stats"]["rows"] == 1
    assert "previewRows" not in item
    preview = json.loads(s3.get_object(Bucket="csv-test-bucket", Key=item["previewKey"])["Body"].read())
    assert preview["rows"] == [["Alice", "10"]]
    glue_table = boto3.client("glue", region_name="us-east-1").get_table(DatabaseName=processor.ATHENA_DATABASE, Name=item["athenaTable"])["Table"]
    assert glue_table["Parameters"]["classification"] == "json"
    assert glue_table["StorageDescriptor"]["Location"].endswith("/athena-v2/")
    assert upload_event.handler(event, None)["startedTasks"] == []
    processor.run()
    assert ecs.run_task.call_count == 1


def test_launch_failure_is_visible(cloud_pipeline):
    table, key, _, ecs, event = cloud_pipeline
    ecs.run_task.return_value = {"failures": [{"reason": "RESOURCE:MEMORY"}]}
    upload_event.handler(event, None)
    assert table.get_item(Key=key)["Item"]["status"] == "failed"


def test_uncertain_launch_reuses_client_token(cloud_pipeline):
    table, key, _, ecs, event = cloud_pipeline
    ecs.run_task.side_effect = TimeoutError("uncertain response")
    with pytest.raises(TimeoutError):
        upload_event.handler(event, None)
    assert table.get_item(Key=key)["Item"]["status"] == "dispatching"
    ecs.run_task.side_effect = None
    upload_event.handler(event, None)
    assert ecs.run_task.call_args_list[0].kwargs == ecs.run_task.call_args_list[1].kwargs
    assert ecs.run_task.call_args.kwargs["clientToken"] == "dataset-1"


def test_deleted_dataset_is_not_recreated(cloud_pipeline):
    table, key, _, ecs, event = cloud_pipeline
    table.delete_item(Key=key)
    upload_event.handler(event, None)
    processor.run()
    assert "Item" not in table.get_item(Key=key)
    ecs.run_task.assert_not_called()


def test_worker_size_limit_marks_failure(cloud_pipeline, monkeypatch):
    table, key, _, _, event = cloud_pipeline
    upload_event.handler(event, None)
    monkeypatch.setattr(processor, "MAX_UPLOAD_BYTES", 5)
    with pytest.raises(ValueError, match="size limit"):
        processor.run()
    assert table.get_item(Key=key)["Item"]["status"] == "failed"


def test_stopped_task_marks_incomplete_dataset_failed(cloud_pipeline):
    table, key, _, _, event = cloud_pipeline
    upload_event.handler(event, None)
    stopped = {"source": "aws.ecs", "detail": {"lastStatus": "STOPPED", "stoppedReason": "CannotPullContainerError", "overrides": {"containerOverrides": [{"name": "csv-processor", "environment": [{"name": "USER_ID", "value": "owner"}, {"name": "DATASET_ID", "value": "dataset-1"}]}]}}}
    assert upload_event.handler(stopped, None) == {"failedTasks": 1}
    assert table.get_item(Key=key)["Item"]["status"] == "failed"
