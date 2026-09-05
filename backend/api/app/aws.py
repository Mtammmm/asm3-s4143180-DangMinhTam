import boto3
from flask import current_app


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
            client.delete_objects(Bucket=bucket, Delete={"Objects": objects, "Quiet": True})


def delete_glue_table(database, table_name):
    if current_app.config["STORAGE_BACKEND"] == "memory" or not table_name:
        return
    client = boto3.client("glue", region_name=current_app.config["AWS_REGION"])
    try:
        client.delete_table(DatabaseName=database, Name=table_name)
    except client.exceptions.EntityNotFoundException:
        pass
