def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_register_login_and_profile(client):
    register = client.post("/auth/register", json={"email": "demo@csvinsight.com", "fullName": "Demo User", "password": "12345678"})
    assert register.status_code == 201
    assert "passwordHash" not in register.get_json()["user"]

    login = client.post("/auth/login", json={"email": "demo@csvinsight.com", "password": "12345678"})
    assert login.status_code == 200
    token = login.get_json()["accessToken"]

    profile = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.get_json()["email"] == "demo@csvinsight.com"


def test_duplicate_registration_is_rejected(client):
    payload = {"email": "demo@csvinsight.com", "fullName": "Demo User", "password": "12345678"}
    assert client.post("/auth/register", json=payload).status_code == 201
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_dataset_create_list_get_and_delete(authenticated_client):
    created = authenticated_client.post("/datasets", json={"name": "orders.csv", "size": 2048, "contentType": "text/csv"})
    assert created.status_code == 201
    payload = created.get_json()
    dataset_id = payload["dataset"]["id"]
    assert payload["dataset"]["status"] == "uploading"
    assert payload["upload"]["method"] == "PUT"

    listed = authenticated_client.get("/datasets")
    assert listed.status_code == 200
    assert len(listed.get_json()) == 1

    details = authenticated_client.get(f"/datasets/{dataset_id}")
    assert details.status_code == 200
    assert details.get_json()["name"] == "orders.csv"

    deleted = authenticated_client.delete(f"/datasets/{dataset_id}")
    assert deleted.status_code == 204
    assert authenticated_client.get(f"/datasets/{dataset_id}").status_code == 404


def test_dataset_requires_authentication(client):
    response = client.get("/datasets")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_invalid_dataset_file_is_rejected(authenticated_client):
    response = authenticated_client.post("/datasets", json={"name": "orders.exe", "size": 100, "contentType": "text/csv"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_password_reset_flow(client):
    payload = {"email": "demo@csvinsight.com", "fullName": "Demo User", "password": "12345678"}
    assert client.post("/auth/register", json=payload).status_code == 201
    requested = client.post("/auth/forgot-password", json={"email": payload["email"]})
    reset_token = requested.get_json()["resetToken"]
    reset = client.post("/auth/reset-password", json={"email": payload["email"], "resetToken": reset_token, "newPassword": "87654321"})
    assert reset.status_code == 200
    assert client.post("/auth/login", json={"email": payload["email"], "password": "87654321"}).status_code == 200
