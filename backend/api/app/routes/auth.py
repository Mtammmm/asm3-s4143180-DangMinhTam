import re
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request

from ..auth import create_access_token
from ..errors import ApiError
from ..store import get_store
from ..aws import send_reset_email


auth_blueprint = Blueprint("auth", __name__)
email_pattern = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def public_user(user):
    return {key: user[key] for key in ("userId", "email", "fullName", "avatarKey", "accountStatus", "createdAt", "updatedAt") if key in user}


@auth_blueprint.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    full_name = str(payload.get("fullName", "")).strip()
    password = str(payload.get("password", ""))
    if not email_pattern.match(email):
        raise ApiError("Enter a valid email address.", 400, "INVALID_EMAIL")
    if len(full_name) < 2 or len(full_name) > 100:
        raise ApiError("Full name must contain between 2 and 100 characters.", 400, "INVALID_NAME")
    if len(password) < 8 or len(password) > 128:
        raise ApiError("Password must contain between 8 and 128 characters.", 400, "INVALID_PASSWORD")
    store = get_store()
    if store.get_user_by_email(email):
        raise ApiError("An account already exists for this email.", 409, "EMAIL_ALREADY_EXISTS")
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "userId": str(uuid.uuid4()),
        "email": email,
        "fullName": full_name,
        "password": password,
        "avatarKey": "",
        "accountStatus": "active",
        "createdAt": now,
        "updatedAt": now,
    }
    store.put_user(user)
    return jsonify({"user": public_user(user), "accessToken": create_access_token(user), "tokenType": "Bearer"}), 201


@auth_blueprint.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = get_store().get_user_by_email(email)
    if not user:
        raise ApiError("Email or password is incorrect.", 401, "INVALID_CREDENTIALS")
    if not secrets.compare_digest(str(user.get("password", "")), password):
        raise ApiError("Email or password is incorrect.", 401, "INVALID_CREDENTIALS")
    if user.get("accountStatus") != "active":
        raise ApiError("This account is not active.", 403, "ACCOUNT_INACTIVE")
    return jsonify({"user": public_user(user), "accessToken": create_access_token(user), "tokenType": "Bearer"})


@auth_blueprint.post("/forgot-password")
def forgot_password():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    store = get_store()
    if not current_app.config["EXPOSE_RESET_TOKEN"] and not current_app.config.get("RESET_EMAIL_SENDER"):
        raise ApiError("Password recovery is not configured. Contact the application administrator.", 503, "RECOVERY_UNAVAILABLE")
    user = store.get_user_by_email(email)
    response = {"message": "If an account exists for that email, a reset request has been created."}
    if not user:
        return jsonify(response)
    reset_token = secrets.token_urlsafe(32)
    store.update_user(
        user["userId"],
        {
            "resetTokenHash": hashlib.sha256(reset_token.encode("utf-8")).hexdigest(),
            "resetTokenExpiresAt": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        },
    )
    if current_app.config["EXPOSE_RESET_TOKEN"]:
        response["resetToken"] = reset_token
    else:
        send_reset_email(email, reset_token)
    return jsonify(response)


@auth_blueprint.post("/reset-password")
def reset_password():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    reset_token = str(payload.get("resetToken", ""))
    new_password = str(payload.get("newPassword", ""))
    if len(new_password) < 8 or len(new_password) > 128:
        raise ApiError("Password must contain between 8 and 128 characters.", 400, "INVALID_PASSWORD")
    store = get_store()
    user = store.get_user_by_email(email)
    supplied_hash = hashlib.sha256(reset_token.encode("utf-8")).hexdigest()
    if not user or not reset_token or not secrets.compare_digest(user.get("resetTokenHash", ""), supplied_hash):
        raise ApiError("The password reset token is invalid.", 400, "INVALID_RESET_TOKEN")
    try:
        expires_at = datetime.fromisoformat(user["resetTokenExpiresAt"])
    except (KeyError, ValueError) as error:
        raise ApiError("The password reset token is invalid.", 400, "INVALID_RESET_TOKEN") from error
    if expires_at <= datetime.now(timezone.utc):
        raise ApiError("The password reset token has expired.", 400, "RESET_TOKEN_EXPIRED")
    if not store.consume_reset_token(
        user["userId"],
        supplied_hash,
        {
            "password": new_password,
            "resetTokenHash": "",
            "resetTokenExpiresAt": "",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        },
    ):
        raise ApiError("The password reset token is invalid or has already been used.", 400, "INVALID_RESET_TOKEN")
    return jsonify({"message": "Password was reset successfully."})
