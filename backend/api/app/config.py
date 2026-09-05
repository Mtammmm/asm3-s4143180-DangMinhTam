import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "aws")
    USERS_TABLE = os.getenv("USERS_TABLE", "CsvInsightUsers")
    DATASETS_TABLE = os.getenv("DATASETS_TABLE", "CsvInsightDatasets")
    UPLOAD_BUCKET = os.getenv("UPLOAD_BUCKET", "")
    AVATAR_BUCKET = os.getenv("AVATAR_BUCKET", "")
    ATHENA_DATABASE = os.getenv("ATHENA_DATABASE", "csv_insight")
    ATHENA_OUTPUT_LOCATION = os.getenv("ATHENA_OUTPUT_LOCATION", "")
    ATHENA_WORKGROUP = os.getenv("ATHENA_WORKGROUP", "primary")
    ATHENA_QUERY_TIMEOUT_SECONDS = int(os.getenv("ATHENA_QUERY_TIMEOUT_SECONDS", "20"))
    JWT_SECRET = os.getenv("JWT_SECRET", "local-development-secret-change-before-deploy")
    JWT_TTL_SECONDS = int(os.getenv("JWT_TTL_SECONDS", "3600"))
    MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    EXPOSE_RESET_TOKEN = os.getenv("EXPOSE_RESET_TOKEN", "false").lower() == "true"
    FRONTEND_ORIGINS = [origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5500").split(",")]
    TESTING = False
