# Runtime changes and deployment checks

These changes are local source changes until the API Lambda, upload-event Lambda, ECS task definition/image, and static frontend are redeployed. Existing AWS resources have not been modified by this review.

## API and frontend

- Set `STORAGE_BACKEND=aws`, a random `JWT_SECRET` of at least 32 characters, and `EXPOSE_RESET_TOKEN=false`. The API fails startup for an empty, short, or known development/placeholder secret. Generate a secret locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and configure it privately.
- Configure `ATHENA_DATABASE=csv_insight`, `ATHENA_OUTPUT_LOCATION=s3://YOUR_UPLOAD_BUCKET/athena-results/`, and `ATHENA_WORKGROUP=primary`. API timeout must exceed `ATHENA_QUERY_TIMEOUT_SECONDS` plus response overhead; keep the total within the API Gateway integration timeout.
- API role needs Athena start/status/results/stop, Glue delete-table, DynamoDB read/query/write, and S3 upload-signing/read/delete access scoped to application resources. The Athena workgroup needs access to the input and result locations.
- Set `FRONTEND_ORIGINS` to the deployed frontend origin (and localhost if required). S3 upload bucket CORS must permit `POST`, `PUT`, and `GET` from that origin. CSV uploads now use signed POST form fields with an exact file-size condition. Deploy `api.js` with the API change; an old PUT-only client cannot upload to the new contract.
- `frontend/config.js` uses localhost:8080 when the frontend is opened on localhost. The configured API Gateway address is used on deployed hosts. An explicit `window.CSV_INSIGHT_API_URL` supplied before config.js overrides either choice.
- Serve the frontend from S3 through CloudFront and verify the deployed page loads the updated assets. Invalidate changed HTML/JS/config paths or use versioned files when deploying.

## Worker and event orchestration

- Rebuild and push the processor image, register a new task-definition revision, and set `PROCESSOR_TASK_DEFINITION` on the upload Lambda to the **explicit revision**, not a moving family name. This keeps `RunTask` retry parameters stable. Configure `ATHENA_DATABASE`, `DATASETS_TABLE`, and `MAX_UPLOAD_BYTES=10485760` in the task environment.
- Worker role needs S3 get/put, DynamoDB get/update, and Glue create-database/create-table/update-table permissions. Use the same database and upload limit in the worker and API.
- Keep the S3 notification filter `datasets/` + `.csv`. The handler additionally accepts only the exact `datasets/{userId}/{datasetId}/source.csv` shape, so derived files do not launch tasks.
- State transitions are `uploading -> dispatching -> processing -> ready/failed`. Conditional updates stop repeated processing and prevent metadata recreation after deletion. RunTask uses the dataset ID as its client token. Transient launch exceptions are retried by Lambda; an explicit ECS failure response marks the dataset failed.
- Configure an EventBridge rule for `source=aws.ecs`, `detail-type=ECS Task State Change`, `detail.lastStatus=STOPPED`, and your **cluster ARN and processor task-definition ARN**. Target the upload-event Lambda. Permit EventBridge to invoke that Lambda. This marks incomplete tasks failed if they stop before the worker can report its result (for example image-pull failure or out of memory). Successful `ready` datasets are unaffected.
- To handle exhausted Lambda launch retries, create a second Lambda function from the same upload-event package/handler, with `DATASETS_TABLE` and its usual region configured. Set that function as the upload-event Lambda's asynchronous **on-failure destination** and permit invocation. Do not point the failure destination at itself. It consumes the destination envelope and marks still-dispatching datasets failed. Normal async retries remain enabled. If your Learner Lab role cannot configure these integrations, infrastructure-failure recovery remains unverified and needs manual intervention.
- Dataset deletion waits until dispatching/processing finishes. It atomically marks `deleting`, removes S3 objects and Glue metadata, then removes DynamoDB metadata. Failed cleanup can be retried from the same delete endpoint.

## Data representation

New datasets use `athena-v2/rows.jsonl` with the Hive JSON SerDe. Each physical line is one JSON object; embedded newlines in cell values are escaped. The worker's normalized rows drive preview, statistics, and Athena. Empty rows are discarded, cells trimmed, short rows padded, duplicate header names suffixed, and excess fields rejected. Headers are limited to 500 columns and 200 characters per source name, with a total metadata byte limit.

Preview rows live in `preview.json` in S3. The API fetches that preview for details; DynamoDB holds metadata only. Old datasets keep their existing Glue table definitions. Upload them again to adopt normalization. Legacy datasets without Athena metadata use preview-only queries, which the frontend labels explicitly.

## Password recovery

Password storage remains unchanged. A reset code is separate from the password and continues to be stored as a SHA-256 digest, with a 15-minute expiry and conditional single-use consumption.

- Local demo: set `STORAGE_BACKEND=memory` and `EXPOSE_RESET_TOKEN=true`. The recovery form fills in the returned test code. No email is sent.
- AWS: configure `RESET_EMAIL_SENDER` with an SES-verified sender and give the API role `ses:SendEmail` access. In an SES sandbox, verify the recipient as well. The API never returns a reset code in AWS mode. If SES is unavailable under the Learner Lab permissions, recovery reports unavailable; do not claim cloud email recovery works until verified.
- The UI requests a code, accepts the code and new password, confirms the password, and returns to sign-in after success. A missing sender configuration returns HTTP 503 consistently. No real email was sent during development tests.

## Verification before demonstration

1. Run `backend/.venv/Scripts/python.exe -m pytest -q`. The suite includes AWS integration simulations using Moto; this does not replace live AWS verification.
2. Open the deployed frontend, register/sign in, upload a CSV with more than 100 rows, and wait for `ready` without running any processing command manually.
3. Verify a query returns matches beyond the preview's first 100 rows and a full match count; show Athena query history and the Glue table.
4. Verify duplicate event delivery does not start another processing attempt after ready, and stopped-task events mark interrupted datasets failed.
5. Delete a ready dataset and verify its S3 prefix, Glue table, and DynamoDB record are removed.
6. Capture the deployed frontend URL, architecture diagram, service screenshots, and test/demo evidence for the assessment document.

## References

[1] Amazon Web Services, "Hive JSON SerDe," *Amazon Athena User Guide*. [Online]. Available: https://docs.aws.amazon.com/athena/latest/ug/hive-json-serde.html. [Accessed: Sep. 5, 2026].

[2] Amazon Web Services, "POST Policy," *Amazon S3 API Reference*. [Online]. Available: https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-HTTPPOSTConstructPolicy.html. [Accessed: Sep. 5, 2026].

[3] Amazon Web Services, "Ensuring idempotency," *Amazon ECS Developer Guide*. [Online]. Available: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_Idempotency.html. [Accessed: Sep. 5, 2026].

Frontend API contract tests (Node.js): `node --test frontend/tests/api.test.cjs`. These tests cover S3 POST uploads, authenticated local uploads, password reset requests, and config overrides; they do not replace browser interaction tests.
