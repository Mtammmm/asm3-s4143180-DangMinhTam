from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request

from ..auth import require_authentication
from ..aws import create_download_url, create_upload_url
from ..errors import ApiError
from ..store import get_store


users_blueprint = Blueprint("users", __name__)


def serialize_user(user):
    response = {key: value for key, value in user.items() if key != "passwordHash"}
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


@users_blueprint.post("/me/avatar/upload-url")
@require_authentication
def create_avatar_upload():
    payload = request.get_json(silent=True) or {}
    content_type = str(payload.get("contentType", ""))
    allowed_types = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    if content_type not in allowed_types:
        raise ApiError("Avatar must be a JPEG, PNG, or WebP image.", 400, "INVALID_AVATAR_TYPE")
    key = f"avatars/{g.current_user['userId']}/profile.{allowed_types[content_type]}"
    user = get_store().update_user(
        g.current_user["userId"],
        {"avatarKey": key, "updatedAt": datetime.now(timezone.utc).isoformat()},
    )
    return jsonify({"avatarKey": key, "upload": create_upload_url(current_app.config["AVATAR_BUCKET"], key, content_type), "user": serialize_user(user)})
