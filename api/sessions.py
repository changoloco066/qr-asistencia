import datetime
import secrets

from flask import Blueprint, jsonify, request

from api.db import get_connection
from api.auth import require_auth

sessions_bp = Blueprint("sessions", __name__)

TOKEN_LIFETIME_SECONDS = 45


@sessions_bp.route("/api/sessions/start", methods=["POST"])
@require_auth
def start_session():
    """Get today's session if it already exists, otherwise create it.
    Idempotent per calendar day -- opening the dashboard twice in one class
    doesn't create duplicate sessions."""
    today = datetime.date.today()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM sessions WHERE session_date = %s", (today,)
            )
            existing = cur.fetchone()

            if existing:
                session_id = existing["id"]
            else:
                cur.execute(
                    "INSERT INTO sessions (session_date) VALUES (%s) RETURNING id",
                    (today,),
                )
                session_id = cur.fetchone()["id"]
                conn.commit()
    finally:
        conn.close()

    return jsonify({"session_id": session_id, "session_date": str(today)})


@sessions_bp.route("/api/sessions/<int:session_id>/token", methods=["POST"])
@require_auth
def rotate_token(session_id):
    """Issue a fresh token for this session, valid for TOKEN_LIFETIME_SECONDS.
    The dashboard calls this on a timer and re-renders the QR with the new token."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT finished FROM sessions WHERE id = %s", (session_id,)
            )
            session_row = cur.fetchone()
            if not session_row:
                return jsonify({"error": "session_not_found"}), 404
            if session_row["finished"]:
                return jsonify({"error": "session_finished"}), 400

            token = secrets.token_urlsafe(24)
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=TOKEN_LIFETIME_SECONDS
            )
            cur.execute(
                """INSERT INTO session_tokens (session_id, token, expires_at)
                   VALUES (%s, %s, %s)""",
                (session_id, token, expires_at),
            )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"token": token, "expires_at": expires_at.isoformat()})


@sessions_bp.route("/api/sessions/today", methods=["GET"])
@require_auth
def get_today_session():
    """Read-only check -- does NOT create a session. Lets the dashboard
    resume an already-started, still-active class on reload without
    accidentally starting one that was never begun."""
    today = datetime.date.today()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, finished FROM sessions WHERE session_date = %s",
                (today,),
            )
            existing = cur.fetchone()
    finally:
        conn.close()

    if not existing:
        return jsonify({"exists": False})

    return jsonify(
        {
            "exists": True,
            "session_id": existing["id"],
            "finished": existing["finished"],
        }
    )


@sessions_bp.route("/api/sessions/<int:session_id>/finish", methods=["POST"])
@require_auth
def finish_session(session_id):
    """Closes today's roll call without deleting anything -- attendance
    already logged stays, but no new tokens can be issued and the dashboard
    stops polling. Different from cancel, which deletes the session entirely."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET finished = TRUE WHERE id = %s", (session_id,)
            )
            updated = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    if not updated:
        return jsonify({"error": "session_not_found"}), 404

    return jsonify({"ok": True})


@sessions_bp.route("/api/sessions/<int:session_id>/reopen", methods=["POST"])
@require_auth
def reopen_session(session_id):
    """Undo an accidental 'Finalizar clase' -- resumes the same session
    instead of making her start a brand new one."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET finished = FALSE WHERE id = %s", (session_id,)
            )
            updated = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    if not updated:
        return jsonify({"error": "session_not_found"}), 404

    return jsonify({"ok": True})


@sessions_bp.route("/api/sessions/today", methods=["DELETE"])
@require_auth
def cancel_today_session():
    """Undo an accidental 'Iniciar clase' click -- removes today's session
    and, via ON DELETE CASCADE, its tokens and any attendance already logged."""
    today = datetime.date.today()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE session_date = %s", (today,))
            deleted = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    if not deleted:
        return jsonify({"error": "no_session_today"}), 404

    return jsonify({"ok": True})


@sessions_bp.route("/api/sessions/<int:session_id>/status", methods=["GET"])
@require_auth
def session_status(session_id):
    """Polled by the dashboard every few seconds to show who has checked in."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM students")
            total_roster = cur.fetchone()["total"]

            cur.execute(
                """SELECT a.matricula, s.full_name, a.checked_in_at
                   FROM attendance a
                   JOIN students s ON s.matricula = a.matricula
                   WHERE a.session_id = %s
                   ORDER BY a.checked_in_at DESC""",
                (session_id,),
            )
            checked_in = cur.fetchall()
    finally:
        conn.close()

    return jsonify(
        {
            "total_roster": total_roster,
            "checked_in_count": len(checked_in),
            "checked_in": checked_in,
        }
    )