# CSV Insight

CSV Insight is a cloud CSV analytics application for AWS Academy Learner Lab. The frontend uploads datasets through presigned S3 URLs, a Lambda function starts an ECS Fargate processor, processed datasets are catalogued in AWS Glue and queried through Amazon Athena, and a Flask API stores application state in DynamoDB.

## Repository layout

```text
.
├── backend/
│   ├── api/                     # Flask API and API Lambda entrypoint
│   ├── functions/upload_event/  # S3 event Lambda
│   ├── workers/csv_processor/   # ECS Fargate processor
│   ├── scripts/                 # Maintenance and seed scripts
│   └── tests/                   # Backend test suite
├── frontend/                    # Static HTML, CSS, and JavaScript client
├── docs/                        # Manual deployment documentation
├── .env.example                 # Local environment template
└── pytest.ini                   # Shared test configuration
```

## Quick start

From the repository root:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
python -m pip install -r backend/api/requirements-dev.txt
python -m pytest -q
python backend/api/run.py
```

Serve the frontend in a second terminal:

```powershell
python -m http.server 5500 --directory frontend
```

Open `http://localhost:5500`.

## Documentation

- Backend behavior and commands: [`backend/README.md`](backend/README.md)
- Frontend behavior and API contract: [`frontend/README.md`](frontend/README.md)
- AWS Learner Lab deployment: [`docs/aws-learner-lab-manual-setup.md`](docs/aws-learner-lab-manual-setup.md)

Keep real credentials in the ignored `.env` file or, preferably, in the AWS CLI `learner-lab` profile. Never commit them.
