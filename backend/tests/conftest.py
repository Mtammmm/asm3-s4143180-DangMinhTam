import pytest

from app import create_app
from app.store import MemoryStore


class TestConfig:
    TESTING = True
    STORAGE_BACKEND = "memory"
    AWS_REGION = "us-east-1"
    USERS_TABLE = "test-users"
    DATASETS_TABLE = "test-datasets"
    UPLOAD_BUCKET = "test-uploads"
    AVATAR_BUCKET = "test-avatars"
    JWT_SECRET = "test-secret-that-is-long-enough"
    JWT_TTL_SECONDS = 3600
    MAX_UPLOAD_BYTES = 10 * 1024 * 1024
    EXPOSE_RESET_TOKEN = True
    FRONTEND_ORIGINS = ["http://localhost:5500"]


@pytest.fixture(autouse=True)
def clear_memory_store():
    MemoryStore.clear()


@pytest.fixture
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    response = client.post("/auth/register", json={"email": "demo@csvinsight.com", "fullName": "Demo User", "password": "12345678"})
    token = response.get_json()["accessToken"]
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client
