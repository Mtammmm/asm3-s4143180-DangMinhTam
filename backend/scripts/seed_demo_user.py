import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from argon2 import PasswordHasher
from boto3.dynamodb.conditions import Key


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    email = os.environ["DEMO_EMAIL"].strip().lower()
    password = os.environ["DEMO_PASSWORD"]
    full_name = os.getenv("DEMO_FULL_NAME", "Demo User").strip()
    region = os.getenv("AWS_REGION", "us-east-1")
    table_name = os.getenv("USERS_TABLE", "CsvInsightUsers")
    table = boto3.resource("dynamodb", region_name=region).Table(table_name)
    existing = table.query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email),
        Limit=1,
    ).get("Items", [])
    if existing:
        raise SystemExit(f"A user already exists for {email}.")
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(
        Item={
            "userId": str(uuid.uuid4()),
            "email": email,
            "fullName": full_name,
            "passwordHash": PasswordHasher().hash(password),
            "avatarKey": "",
            "accountStatus": "active",
            "createdAt": now,
            "updatedAt": now,
        }
    )
    print(f"Created demo user {email} in {table_name}.")


if __name__ == "__main__":
    main()
