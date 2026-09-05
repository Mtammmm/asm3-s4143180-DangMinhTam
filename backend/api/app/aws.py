import json

import boto3
from flask import current_app
from botocore.exceptions import ClientError

from .errors import ApiError


def create_upload_url(bucket, key, content_type):
    if current_app.config["STORAGE_BACKEND"] == "memory":
        return {"url": f"https://local-upload.invalid/{key}", "method": "PUT", "expiresIn": 900}
    client = boto3.client("s3", region_name=current_app.config["AWS_REGION"])
    url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=900,
    )
    return {"url": url, "method": "PUT", "expiresIn": 900}


def create_dataset_upload(bucket, key, content_type, size):
    # [2] Amazon Web Services, "POST Policy," Amazon S3 API Reference.
    # https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-HTTPPOSTConstructPolicy.html (accessed Sep. 5, 2026).
    client = boto3.client("s3", region_name=current_app.config["AWS_REGION"])
    result = client.generate_presigned_post(
        Bucket=bucket, Key=key,
        Fields={"Content-Type": content_type},
        Conditions=[{"Content-Type": content_type}, ["content-length-range", size, size]],
        ExpiresIn=900,
    )
    return {**result, "method": "POST", "expiresIn": 900}


def read_preview(bucket, key):
    client = boto3.client("s3", region_name=current_app.config["AWS_REGION"])
    response = client.get_object(Bucket=bucket, Key=key)
    try:
        return json.loads(response["Body"].read())
    finally:
        response["Body"].close()


def send_reset_email(email, token):
    client = boto3.client("ses", region_name=current_app.config["AWS_REGION"])
    try:
        client.send_email(
            Source=current_app.config["RESET_EMAIL_SENDER"],
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": "CSV Insight password reset", "Charset": "UTF-8"},
                "Body": {"Text": {"Data": f"Enter this code in CSV Insight to reset your password:\n\n{token}\n\nThis code expires in 15 minutes. If you did not request it, ignore this email.", "Charset": "UTF-8"}},
            },
        )
    except ClientError as error:
        current_app.logger.error("Password recovery email failed: %s", error.response["Error"]["Code"])
        raise ApiError("Recovery email could not be sent. Try again later.", 503, "RECOVERY_DELIVERY_FAILED") from error


def create_download_url(bucket, key):
    if not key:
        return None
    if current_app.config["STORAGE_BACKEND"] == "memory":
        return f"https://local-download.invalid/{key}"
    client = boto3.client("s3", region_name=current_app.config["AWS_REGION"])
    return client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=900)


def delete_prefix(bucket, prefix):
    if current_app.config["STORAGE_BACKEND"] == "memory" or not bucket:
        return
    client = boto3.client("s3", region_name=current_app.config["AWS_REGION"])
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if objects:
            response = client.delete_objects(Bucket=bucket, Delete={"Objects": objects, "Quiet": True})
            if response.get("Errors"):
                raise ApiError("Some dataset files could not be deleted. Retry deletion.", 502, "DELETE_INCOMPLETE")


def delete_glue_table(database, table_name):
    if current_app.config["STORAGE_BACKEND"] == "memory" or not table_name:
        return
    client = boto3.client("glue", region_name=current_app.config["AWS_REGION"])
    try:
        client.delete_table(DatabaseName=database, Name=table_name)
    except client.exceptions.EntityNotFoundException:
        pass
