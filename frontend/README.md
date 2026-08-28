# CSV Insight frontend

Production-shaped frontend prototype for the Cloud CSV Analytics Dashboard. It is built with plain HTML, CSS, and JavaScript so it can be hosted directly from Amazon S3 and delivered through CloudFront.

## Run locally

```bash
python -m http.server 5500 --directory frontend
```

Open `http://localhost:5500`.

Authentication uses the Flask backend. Start it on `http://localhost:8080`, then register an account from the frontend. Passwords are hashed by the backend and stored in the configured user store.

## Completed frontend flows

- Responsive landing page with light and dark themes.
- Sign in, sign up, forgot password, session persistence, and sign out states.
- Authenticated dashboard and analyzer navigation.
- CSV drag and drop, file validation, parsing, preview, search, and statistics.
- Dataset library with loading, error, empty, filtered, and populated states.
- Dataset details and tabular preview.
- Simple column queries: contains, equals, greater than, less than, and empty.
- Dataset deletion with confirmation and success feedback.
- Keyboard focus styles, labeled fields, live regions, and native accessible dialogs.

## Service boundary

Set the API base URL in `config.js`. It defaults to the local Flask backend; replace it with the API Gateway URL for deployment:

```html
<script>window.CSV_INSIGHT_API_URL = "https://api.example.com/v1";</script>
```

For an authenticated API Gateway route, expose an async token provider before `api.js` loads:

```html
<script>
  window.CSV_INSIGHT_GET_TOKEN = async function getToken() {
    return "access-token-from-your-identity-provider";
  };
</script>
```

The frontend expects these endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/datasets` | List datasets owned by the signed-in user |
| `POST` | `/datasets` | Create a dataset and return its metadata, statistics, headers, and preview rows |
| `GET` | `/datasets/{datasetId}` | Get dataset details and preview rows |
| `POST` | `/datasets/{datasetId}/query` | Execute a simple analytical query |
| `DELETE` | `/datasets/{datasetId}` | Delete the dataset and related metadata |

All non-empty responses must use JSON. Errors should return `{ "message": "Readable error message" }` with the appropriate HTTP status.

## Dataset response shape

```json
{
  "id": "dataset-id",
  "name": "orders.csv",
  "size": 2048,
  "status": "ready",
  "createdAt": "2026-08-27T10:00:00.000Z",
  "stats": {
    "rows": 120,
    "columns": 8,
    "missingValues": 4,
    "completeness": 99
  },
  "headers": ["order_id", "customer"],
  "rows": [["ORD-1001", "Alex Morgan"]]
}
```

List responses may omit `headers` and `rows`. Query responses must return `headers`, `rows`, and `count`.

## AWS integration notes

- API Gateway should expose the REST routes listed above.
- Lambda should validate ownership, orchestrate uploads, write DynamoDB metadata, and start processing.
- For large files, replace the JSON create request with a presigned S3 upload flow while keeping the public `DatasetApi` methods unchanged.
- ECS Fargate should calculate statistics and update dataset status from `processing` to `ready` or `failed`.
- Athena query results should be normalized to the query response shape expected by the UI.
- CloudFront should serve this directory and route API traffic to API Gateway if a shared domain is used.
