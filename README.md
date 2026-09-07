# CSV Insight

CSV analytics application with a static frontend, Flask API, DynamoDB, S3, ECS and Glue/Athena.

- backend/api/: Flask application and Lambda entrypoint.
- backend/functions/: upload and task-event Lambda handler.
- backend/workers/: CSV processor and Dockerfile.
- backend/scripts/: account seed script.
- backend/tests/, frontend/tests/: automated tests.
- frontend/: HTML, CSS, JavaScript and required images.

## Run locally

From the repository root in PowerShell:

    python -m venv backend/.venv
    & backend/.venv/Scripts/python.exe -m pip install -r backend/api/requirements-dev.txt
    $env:STORAGE_BACKEND = "memory"
    $env:EXPOSE_RESET_TOKEN = "true"
    & backend/.venv/Scripts/python.exe backend/api/run.py

In a second terminal:

    python -m http.server 5500 --directory frontend

Open http://localhost:5500. Local CSV data disappears when the API restarts. Local avatar uploads require AWS.

Use .env.example for configuration. Keep real credentials in ignored .env or a local AWS profile. AWS mode requires a random JWT secret of at least 32 characters and EXPOSE_RESET_TOKEN=false. Password storage remains unchanged.

## Check the code

    & backend/.venv/Scripts/python.exe -m pytest -q
    node --test frontend/tests/api.test.cjs

Build the worker with docker build -t csv-insight-processor backend/workers/csv_processor. Frontend API selection is in frontend/config.js.
