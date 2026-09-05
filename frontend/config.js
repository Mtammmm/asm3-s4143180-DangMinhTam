// An explicit value set before this script takes precedence, including "" for the dataset mock.
window.CSV_INSIGHT_API_URL ??= ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname)
  ? "http://localhost:8080"
  : "https://ld3a2ycupd.execute-api.us-east-1.amazonaws.com";
