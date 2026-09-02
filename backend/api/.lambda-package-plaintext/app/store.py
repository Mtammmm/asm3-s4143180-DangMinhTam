from copy import deepcopy
from decimal import Decimal
from threading import Lock

import boto3
from boto3.dynamodb.conditions import Key
from flask import current_app


def _convert_numbers(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, list):
        return [_convert_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: _convert_numbers(item) for key, item in value.items()}
    return value


class MemoryStore:
    users = {}
    datasets = {}
    lock = Lock()

    @classmethod
    def clear(cls):
        with cls.lock:
            cls.users = {}
            cls.datasets = {}

    def get_user_by_id(self, user_id):
        return deepcopy(self.users.get(user_id))

    def get_user_by_email(self, email):
        return next((deepcopy(user) for user in self.users.values() if user["email"] == email), None)

    def put_user(self, user):
        with self.lock:
            self.users[user["userId"]] = deepcopy(user)
        return deepcopy(user)

    def update_user(self, user_id, changes):
        with self.lock:
            self.users[user_id].update(deepcopy(changes))
            return deepcopy(self.users[user_id])

    def list_datasets(self, user_id):
        items = [deepcopy(item) for (owner, _), item in self.datasets.items() if owner == user_id]
        return sorted(items, key=lambda item: item["createdAt"], reverse=True)

    def get_dataset(self, user_id, dataset_id):
        return deepcopy(self.datasets.get((user_id, dataset_id)))

    def put_dataset(self, dataset):
        with self.lock:
            self.datasets[(dataset["userId"], dataset["datasetId"])] = deepcopy(dataset)
        return deepcopy(dataset)

    def delete_dataset(self, user_id, dataset_id):
        with self.lock:
            return self.datasets.pop((user_id, dataset_id), None) is not None


class DynamoStore:
    def __init__(self):
        resource = boto3.resource("dynamodb", region_name=current_app.config["AWS_REGION"])
        self.users = resource.Table(current_app.config["USERS_TABLE"])
        self.datasets = resource.Table(current_app.config["DATASETS_TABLE"])

    def get_user_by_id(self, user_id):
        return _convert_numbers(self.users.get_item(Key={"userId": user_id}).get("Item"))

    def get_user_by_email(self, email):
        response = self.users.query(IndexName="email-index", KeyConditionExpression=Key("email").eq(email), Limit=1)
        items = response.get("Items", [])
        return _convert_numbers(items[0]) if items else None

    def put_user(self, user):
        self.users.put_item(Item=user, ConditionExpression="attribute_not_exists(userId)")
        return user

    def update_user(self, user_id, changes):
        names = {f"#field{index}": key for index, key in enumerate(changes)}
        values = {f":value{index}": value for index, value in enumerate(changes.values())}
        assignments = ", ".join(f"{name} = {value}" for name, value in zip(names, values))
        response = self.users.update_item(
            Key={"userId": user_id},
            UpdateExpression=f"SET {assignments}",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return _convert_numbers(response["Attributes"])

    def list_datasets(self, user_id):
        response = self.datasets.query(KeyConditionExpression=Key("userId").eq(user_id), ScanIndexForward=False)
        items = _convert_numbers(response.get("Items", []))
        return sorted(items, key=lambda item: item["createdAt"], reverse=True)

    def get_dataset(self, user_id, dataset_id):
        response = self.datasets.get_item(Key={"userId": user_id, "datasetId": dataset_id})
        return _convert_numbers(response.get("Item"))

    def put_dataset(self, dataset):
        self.datasets.put_item(Item=dataset)
        return dataset

    def delete_dataset(self, user_id, dataset_id):
        self.datasets.delete_item(Key={"userId": user_id, "datasetId": dataset_id})
        return True


def get_store():
    return MemoryStore() if current_app.config["STORAGE_BACKEND"] == "memory" else DynamoStore()
