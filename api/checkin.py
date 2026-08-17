import datetime

from flask import Blueprint, jsonify, request

from api.db import get_connection

checkin_bp = Blueprint("checkin", __name__)


@checkin_bp.route("/api/checkin", methods=["POST"])
def checkin():
    """Public endpoint -- this is what a student's browser hits after scanning
    the QR. No auth required (that's the point), but every write is scoped
    to exactly one attendance row for the matricula given, nothing else
    is readable or writable from here."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    token = (data.get("token") or "").strip()
    matricula = (data.get("matricula") or "").strip()

    if not session_id or not token or not matricula:
        return jsonify({"error": "missing_fields"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 0. session must exist and not already be finished
            cur.execute(
                "SELECT finished FROM sessions WHERE id = %s", (session_id,)
            )
            session_row = cur.fetchone()
            if not session_row:
                return jsonify({"error": "session_not_found"}), 404
            if session_row["finished"]:
                return jsonify({"error": "session_finished"}), 400

            # 1. token must exist for this session and not be expired
            cur.execute(
                """SELECT 1 FROM session_tokens
                   WHERE session_id = %s AND token = %s AND expires_at > %s""",
                (session_id, token, datetime.datetime.utcnow()),
            )
            if not cur.fetchone():
                return jsonify({"error": "expired_or_invalid_token"}), 400

            # 2. matricula must be on the roster
            cur.execute(
                "SELECT full_name FROM students WHERE matricula = %s", (matricula,)
            )
            student = cur.fetchone()
            if not student:
                return jsonify({"error": "matricula_not_found"}), 404

            # 3. record attendance -- unique (session_id, matricula) stops double check-in
            cur.execute(
                """INSERT INTO attendance (session_id, matricula)
                   VALUES (%s, %s)
                   ON CONFLICT (session_id, matricula) DO NOTHING
                   RETURNING id""",
                (session_id, matricula),
            )
            inserted = cur.fetchone()
            conn.commit()

            if not inserted:
                return jsonify({"error": "already_checked_in"}), 409

    finally:
        conn.close()

    return jsonify({"ok": True, "full_name": student["full_name"]}), 201