from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, request

from .errors import ApiError


def create_access_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["userId"],
        "email": user["email"],
        "iat": now,
        "exp": now + timedelta(seconds=current_app.config["JWT_TTL_SECONDS"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def require_authentication(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise ApiError("A valid Bearer token is required.", 401, "AUTHENTICATION_REQUIRED")
        try:
            claims = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"],
                                options={"require": ["sub", "email", "iat", "exp"]})
        except jwt.ExpiredSignatureError as error:
            raise ApiError("Your session has expired.", 401, "TOKEN_EXPIRED") from error
        except jwt.InvalidTokenError as error:
            raise ApiError("The access token is invalid.", 401, "INVALID_TOKEN") from error
        g.current_user = {"userId": claims["sub"], "email": claims["email"]}
        return view(*args, **kwargs)

    return wrapped
