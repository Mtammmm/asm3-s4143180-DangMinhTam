import secrets

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from .config import Config
from .errors import ApiError
from .routes.auth import auth_blueprint
from .routes.datasets import datasets_blueprint
from .routes.users import users_blueprint


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    secret = app.config.get("JWT_SECRET", "")
    if app.config["STORAGE_BACKEND"] == "aws":
        if len(secret) < 32 or secret.startswith(("local-", "replace-", "test-")):
            raise ValueError("AWS mode requires a random JWT_SECRET of at least 32 characters.")
        if app.config["EXPOSE_RESET_TOKEN"]:
            raise ValueError("EXPOSE_RESET_TOKEN must be false in AWS mode; configure RESET_EMAIL_SENDER for email recovery.")
    elif not secret:
        app.config["JWT_SECRET"] = secrets.token_urlsafe(48)
    app.config["MAX_CONTENT_LENGTH"] = app.config["MAX_UPLOAD_BYTES"] + 65536
    CORS(
        app,
        resources={r"/*": {"origins": app.config["FRONTEND_ORIGINS"]}},
        allow_headers=["Authorization", "Content-Type"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    app.register_blueprint(auth_blueprint, url_prefix="/auth")
    app.register_blueprint(users_blueprint, url_prefix="/users")
    app.register_blueprint(datasets_blueprint, url_prefix="/datasets")

    @app.get("/health")
    def health_check():
        return jsonify({"status": "healthy", "service": "csv-insight-api"})

    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return jsonify({"error": {"code": error.code, "message": error.message}}), error.status_code

    @app.errorhandler(404)
    def handle_not_found(_error):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "The requested resource was not found."}}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_error):
        return jsonify({"error": {"code": "METHOD_NOT_ALLOWED", "message": "This HTTP method is not supported."}}), 405

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException):
            return jsonify({"error": {"code": "HTTP_ERROR", "message": error.description}}), error.code
        app.logger.exception("Unhandled application error", exc_info=error)
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": "An unexpected server error occurred."}}), 500

    return app
