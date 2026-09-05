# CSV Insight Flask backend

Flask REST API, DynamoDB persistence, presigned S3 uploads, Lambda orchestration, and an ECS Fargate CSV processor for AWS Academy Learner Lab.

## Implemented API

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | No | Health check |
| `POST` | `/auth/register` | No | Create a user account |
| `POST` | `/auth/login` | No | Verify credentials and issue a JWT |
| `POST` | `/auth/forgot-password` | No | Create a 15-minute password reset token |
| `POST` | `/auth/reset-password` | No | Replace the password using a valid reset token |
| `GET` | `/users/me` | Bearer JWT | Read the current profile |
| `PATCH` | `/users/me` | Bearer JWT | Update the current profile |
| `POST` | `/users/me/password` | Bearer JWT | Verify and replace the current password |
| `POST` | `/users/me/avatar/upload-url` | Bearer JWT | Create an avatar presigned upload URL |
| `PATCH` | `/users/me/avatar` | Bearer JWT | Confirm an uploaded avatar and update the profile |
| `GET` | `/datasets` | Bearer JWT | List owned datasets |
| `POST` | `/datasets` | Bearer JWT | Create metadata and a CSV presigned upload URL |
| `GET` | `/datasets/{id}` | Bearer JWT | Read owned dataset details |
| `DELETE` | `/datasets/{id}` | Bearer JWT | Delete S3 objects and metadata |
| `POST` | `/datasets/{id}/query` | Bearer JWT | Query the complete CSV dataset with Amazon Athena |

## Local setup

Create a virtual environment and install API dependencies:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/api/requirements-dev.txt
```

Run without AWS by using the in-memory store:

```powershell
$env:STORAGE_BACKEND = "memory"
$env:JWT_SECRET = "local-development-secret-with-at-least-32-characters"
$env:FRONTEND_ORIGINS = "http://localhost:5500"
python backend/api/run.py
```

The API is available at `http://localhost:8080`.

Run tests:

```powershell
python -m pytest -q
```

## Directory layout

```text
backend/
├── api/                     # Flask API, local entrypoint, and API Lambda entrypoint
├── functions/upload_event/  # S3-triggered orchestration Lambda
├── workers/csv_processor/   # One-shot ECS Fargate CSV processor
├── scripts/                 # Operational and seed scripts
└── tests/                   # API and processor tests
```

## Local connection to Learner Lab

Refresh the temporary credentials in the `learner-lab` AWS profile, then run:

```powershell
$env:AWS_PROFILE = "learner-lab"
$env:AWS_REGION = "us-east-1"
$env:STORAGE_BACKEND = "aws"
$env:USERS_TABLE = "CsvInsightUsers"
$env:DATASETS_TABLE = "CsvInsightDatasets"
$env:UPLOAD_BUCKET = "stack-output-upload-bucket"
$env:AVATAR_BUCKET = "stack-output-avatar-bucket"
$env:ATHENA_DATABASE = "csv_insight"
$env:ATHENA_OUTPUT_LOCATION = "s3://stack-output-upload-bucket/athena-results/"
$env:ATHENA_WORKGROUP = "primary"
$env:JWT_SECRET = "a-long-random-development-secret"
python backend/api/run.py
```

As a local-only shortcut, copy `.env.example` to `.env` and fill the three temporary Learner Lab credential variables. `python-dotenv` loads this file automatically. The populated `.env` is ignored by Git and must never be committed or shared. Replace all three credential values whenever Learner Lab starts a new session.

Do not add AWS credentials or `.env` files to the repository.

## AWS deployment

Follow [`../docs/aws-learner-lab-manual-setup.md`](../docs/aws-learner-lab-manual-setup.md) to deploy with the AWS Console and CLI. The processor image is built and pushed with:

```powershell
$accountId = aws sts get-caller-identity --query Account --output text --profile learner-lab
$region = "us-east-1"
$repository = "$accountId.dkr.ecr.$region.amazonaws.com/csv-insight-processor"
aws ecr get-login-password --region $region --profile learner-lab | docker login --username AWS --password-stdin "$accountId.dkr.ecr.$region.amazonaws.com"
docker build -t csv-insight-processor backend/workers/csv_processor
docker tag csv-insight-processor:latest "${repository}:latest"
docker push "${repository}:latest"
```

## Processing workflow

1. The client creates a dataset through Flask.
2. Flask stores `uploading` metadata in DynamoDB and returns a presigned S3 URL.
3. The client uploads the CSV directly to S3.
4. The S3 event invokes `UploadEventFunction`.
5. The function conditionally claims `uploading` metadata as `dispatching` and invokes Fargate with a stable idempotency token. The worker atomically claims `processing`.
6. The processor validates actual upload size, normalizes CSV, writes the preview to S3, and registers normalized JSON Lines in Glue. Athena and the preview use the same data.
7. The API runs full-dataset filters through Amazon Athena while preserving the frontend response shape.
8. Processing errors change the status to `failed` with a bounded error message.

## Demo user seed

The seed script reads its password from the environment:

```powershell
$env:AWS_PROFILE = "learner-lab"
$env:DEMO_EMAIL = "demo@csvinsight.com"
$env:DEMO_PASSWORD = "replace-this-before-running"
$env:DEMO_FULL_NAME = "Demo User"
python backend/scripts/seed_demo_user.py
Remove-Item Env:DEMO_PASSWORD
```

## Current boundary

The ECS processor writes normalized JSON Lines into an isolated `athena-v2/` S3 prefix and registers a Hive JSON SerDe table in Glue. Duplicate headers receive unique display names. CSV rows with excess fields and files exceeding the configured size limit are rejected. Preview rows are stored in S3, not DynamoDB. The query endpoint executes SQL through Amazon Athena and returns at most 100 matching rows together with the full match count. Datasets created before Athena was enabled continue to use preview querying until they are reprocessed.

Required runtime settings:

- API Lambda: `ATHENA_DATABASE`, `ATHENA_OUTPUT_LOCATION`, `ATHENA_WORKGROUP`, and optionally `ATHENA_QUERY_TIMEOUT_SECONDS`.
- ECS processor: `ATHENA_DATABASE`.
- The runtime role needs Glue Data Catalog access, Athena query access, and read/write access to the upload bucket and Athena result prefix.

## Runtime and recovery updates

See [`../docs/reliability-deployment.md`](../docs/reliability-deployment.md) before deploying this revision. AWS mode requires a random JWT secret of at least 32 characters and disallows `EXPOSE_RESET_TOKEN=true`. Local mode may expose a recovery code for testing. For email delivery configure `RESET_EMAIL_SENDER` and SES permissions. Password values remain stored directly as required for this project; this revision does not add password hashing.

Local mode exposes authenticated `PUT /datasets/{id}/content` for actual CSV bytes and queries all uploaded rows. Its response preview is capped at 100 rows. The runtime imports the shared parser from `backend/workers`. The deployed Lambda does not use that local-only route.

Deletion is rejected while a dataset is dispatching or processing; a conditional `deleting` transition prevents races with the upload event. Failed cleanup can be retried. Configure the stopped-task and launch-failure handling described in the deployment notes to avoid unfinished datasets after infrastructure failures.
