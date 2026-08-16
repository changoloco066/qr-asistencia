import os
import datetime
from functools import wraps

import jwt
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash

from api.db import get_connection

auth_bp = Blueprint("auth", __name__)

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
TOKEN_EXP_HOURS = 12


def generate_token(teacher_id, username):
    payload = {
        "teacher_id": teacher_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXP_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def require_auth(fn):
    """Decorator for any endpoint only the teacher should reach.
    Expects 'Authorization: Bearer <token>'."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "missing_token"}), 401
        token = header.split(" ", 1)[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "invalid_token"}), 401
        request.teacher = payload
        return fn(*args, **kwargs)

    return wrapper


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "missing_fields"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash FROM teachers WHERE username = %s",
                (username,),
            )
            teacher = cur.fetchone()
    finally:
        conn.close()

    if not teacher or not check_password_hash(teacher["password_hash"], password):
        # Same generic error either way -- don't reveal whether the username exists.
        return jsonify({"error": "invalid_credentials"}), 401

    token = generate_token(teacher["id"], teacher["username"])
    return jsonify({"token": token})
