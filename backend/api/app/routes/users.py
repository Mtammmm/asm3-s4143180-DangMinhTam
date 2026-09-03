import secrets
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request

from ..auth import require_authentication
from ..aws import create_download_url, create_upload_url
from ..errors import ApiError
from ..store import get_store


users_blueprint = Blueprint("users", __name__)


def serialize_user(user):
    response = {key: value for key, value in user.items() if key not in {"password", "passwordHash"}}
    response["avatarUrl"] = create_download_url(current_app.config["AVATAR_BUCKET"], user.get("avatarKey"))
    return response


@users_blueprint.get("/me")
@require_authentication
def get_profile():
    user = get_store().get_user_by_id(g.current_user["userId"])
    if not user:
        raise ApiError("User profile was not found.", 404, "USER_NOT_FOUND")
    return jsonify(serialize_user(user))


@users_blueprint.patch("/me")
@require_authentication
def update_profile():
    payload = request.get_json(silent=True) or {}
    full_name = str(payload.get("fullName", "")).strip()
    if len(full_name) < 2 or len(full_name) > 100:
        raise ApiError("Full name must contain between 2 and 100 characters.", 400, "INVALID_NAME")
    user = get_store().update_user(
        g.current_user["userId"],
        {"fullName": full_name, "updatedAt": datetime.now(timezone.utc).isoformat()},
    )
    return jsonify(serialize_user(user))


@users_blueprint.post("/me/password")
@require_authentication
def change_password():
    payload = request.get_json(silent=True) or {}
    current_password = str(payload.get("currentPassword", ""))
    new_password = str(payload.get("newPassword", ""))
    if len(new_password) < 8 or len(new_password) > 128:
        raise ApiError("Password must contain between 8 and 128 characters.", 400, "INVALID_PASSWORD")
    if current_password == new_password:
        raise ApiError("Choose a new password that differs from your current password.", 400, "PASSWORD_UNCHANGED")
    store = get_store()
    user = store.get_user_by_id(g.current_user["userId"])
    if not user or not secrets.compare_digest(str(user.get("password", "")), current_password):
        raise ApiError("Your current password is incorrect.", 401, "INVALID_CURRENT_PASSWORD")
    store.update_user(
        g.current_user["userId"],
        {
            "password": new_password,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        },
    )
    return jsonify({"message": "Password updated successfully."})


@users_blueprint.post("/me/avatar/upload-url")
@require_authentication
def create_avatar_upload():
    payload = request.get_json(silent=True) or {}
    content_type = str(payload.get("contentType", ""))
    allowed_types = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    if content_type not in allowed_types:
        raise ApiError("Avatar must be a JPEG, PNG, or WebP image.", 400, "INVALID_AVATAR_TYPE")
    key = f"avatars/{g.current_user['userId']}/profile.{allowed_types[content_type]}"
    return jsonify({"avatarKey": key, "upload": create_upload_url(current_app.config["AVATAR_BUCKET"], key, content_type)})


@users_blueprint.patch("/me/avatar")
@require_authentication
def confirm_avatar_upload():
    payload = request.get_json(silent=True) or {}
    avatar_key = str(payload.get("avatarKey", "")).strip()
    expected_prefix = f"avatars/{g.current_user['userId']}/profile."
    if not avatar_key.startswith(expected_prefix) or avatar_key.rsplit(".", 1)[-1] not in {"jpg", "png", "webp"}:
        raise ApiError("The avatar upload could not be verified.", 400, "INVALID_AVATAR_KEY")
    user = get_store().update_user(
        g.current_user["userId"],
        {"avatarKey": avatar_key, "updatedAt": datetime.now(timezone.utc).isoformat()},
    )
    return jsonify(serialize_user(user))
