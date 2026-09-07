import json
from unittest.mock import Mock

import pytest

from app.athena import run_query
from app.store import MemoryStore
from csv_processor import main as processor


def test_unicode_password_login_and_change_preserve_plaintext_storage(client):
    original = "Mật khẩu thử 123"
    changed = "Mật khẩu mới 456"
    account = {"email": "unicode@example.com", "fullName": "Test User", "password": original}
    registered = client.post("/auth/register", json=account)
    assert registered.status_code == 201
    assert client.post("/auth/login", json=account).status_code == 200
    assert client.post("/auth/login", json={**account, "password": "Mật khẩu sai 123"}).status_code == 401
    token = registered.get_json()["accessToken"]
    response = client.post(
        "/users/me/password", json={"currentPassword": original, "newPassword": changed},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert client.post("/auth/login", json={**account, "password": changed}).status_code == 200
    assert next(iter(MemoryStore.users.values()))["password"] == changed


def test_large_details_and_query_keep_complete_cells_and_total_count(authenticated_client):
    cell = "ệ" * 10000
    content = ("name,notes\n" + f"Alice,{cell}\n" * 99).encode("utf-8")
    created = authenticated_client.post("/datasets", json={"name": "wide.csv", "size": len(content)}).get_json()
    dataset_id = created["dataset"]["id"]
    uploaded = authenticated_client.put(f"/datasets/{dataset_id}/content", data=content, content_type="text/csv")
    assert uploaded.status_code == 200
    details = authenticated_client.get(f"/datasets/{dataset_id}")
    assert details.status_code == 200
    assert len(details.data) < 1_100_000
    assert details.get_json()["rowsTruncated"] is True
    assert details.get_json()["stats"]["rows"] == 99
    assert 0 < len(details.get_json()["rows"]) < 99
    assert all(row == ["Alice", cell] for row in details.get_json()["rows"])
    query = authenticated_client.post(
        f"/datasets/{dataset_id}/query", json={"column": "name", "operator": "equals", "value": "Alice"},
    )
    assert query.status_code == 200
    assert len(query.data) < 1_100_000
    assert query.get_json()["count"] == 99
    assert query.get_json()["rowsTruncated"] is True
    assert query.get_json()["rows"] == details.get_json()["rows"]


def test_worker_preview_keeps_unicode_cells_within_encoded_budget():
    headers = ["name", "notes"]
    rows = [["Alice", "ệ" * 10000] for _ in range(99)]
    preview = processor.create_preview(headers, rows)
    assert len(json.dumps(preview, ensure_ascii=True).encode("utf-8")) <= processor.MAX_PREVIEW_BYTES
    assert preview["rowsTruncated"] is True
    assert 0 < len(preview["rows"]) < len(rows)
    assert preview["rows"] == rows[:len(preview["rows"])]
    assert len(rows) == 99


def test_worker_rejects_one_row_larger_than_display_budget():
    with pytest.raises(ValueError, match="too large to preview"):
        processor.create_preview(["notes"], [["x" * (processor.MAX_PREVIEW_BYTES + 1)]])


@pytest.mark.parametrize("byte_limit, expected_rows", [(1024, 3), (35, 1)])
def test_athena_follows_pages_and_preserves_total_when_display_is_limited(app, monkeypatch, byte_limit, expected_rows):
    def row(*values):
        return {"Data": [{"VarCharValue": value} for value in values]}

    client = Mock()
    client.start_query_execution.return_value = {"QueryExecutionId": "query-1"}
    client.get_query_execution.return_value = {"QueryExecution": {"Status": {"State": "SUCCEEDED"}}}
    client.get_query_results.side_effect = [
        {"ResultSet": {"Rows": [row("name", "notes", "__csv_insight_total"), row("Alice", "first", "125")]}, "NextToken": "page-2"},
        {"ResultSet": {"Rows": [row("Bob", "second", "125"), row("Cara", "third", "125")]}},
    ]
    monkeypatch.setattr("app.athena.boto3.client", lambda *_args, **_kwargs: client)
    monkeypatch.setattr("app.response_limits.MAX_RESPONSE_ROW_BYTES", byte_limit)
    columns = [{"source": "name", "name": "name"}, {"source": "notes", "name": "notes"}]
    with app.app_context():
        rows, count = run_query("dataset_abc", columns, "name", "contains", "")
    assert count == 125
    assert rows == [["Alice", "first"], ["Bob", "second"], ["Cara", "third"]][:expected_rows]
    assert client.get_query_results.call_args.kwargs["NextToken"] == "page-2"
