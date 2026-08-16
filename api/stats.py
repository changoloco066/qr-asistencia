from flask import Blueprint, jsonify

from api.db import get_connection
from api.auth import require_auth

stats_bp = Blueprint("stats", __name__)

AT_RISK_THRESHOLD_PCT = 80


@stats_bp.route("/api/stats/summary", methods=["GET"])
@require_auth
def summary():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM sessions")
            total_sessions = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS total FROM students")
            total_students = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS total FROM attendance")
            total_checkins = cur.fetchone()["total"]
    finally:
        conn.close()

    possible = total_sessions * total_students
    avg_attendance = round((total_checkins / possible) * 100, 1) if possible else 0

    return jsonify(
        {
            "total_sessions": total_sessions,
            "total_students": total_students,
            "average_attendance_pct": avg_attendance,
        }
    )


@stats_bp.route("/api/stats/students", methods=["GET"])
@require_auth
def student_stats():
    """One row per student: how many of the sessions held so far they attended.
    Sorted worst-attendance-first so the professor sees who's at risk without
    having to scan the whole list."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM sessions")
            total_sessions = cur.fetchone()["total"]

            cur.execute(
                """SELECT s.matricula, s.full_name, COUNT(a.id) AS attended
                   FROM students s
                   LEFT JOIN attendance a ON a.matricula = s.matricula
                   GROUP BY s.matricula, s.full_name
                   ORDER BY s.full_name"""
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    result = []
    for r in rows:
        pct = (
            round((r["attended"] / total_sessions) * 100, 1)
            if total_sessions
            else 0
        )
        result.append(
            {
                "matricula": r["matricula"],
                "full_name": r["full_name"],
                "attended": r["attended"],
                "total_sessions": total_sessions,
                "attendance_pct": pct,
                "absences": total_sessions - r["attended"],
                "at_risk": pct < AT_RISK_THRESHOLD_PCT,
            }
        )

    result.sort(key=lambda x: x["attendance_pct"])
    return jsonify(result)


@stats_bp.route("/api/stats/students/<matricula>", methods=["GET"])
@require_auth
def student_detail(matricula):
    """Session-by-session breakdown for one student -- present/absent per date."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT full_name FROM students WHERE matricula = %s", (matricula,)
            )
            student = cur.fetchone()
            if not student:
                return jsonify({"error": "matricula_not_found"}), 404

            cur.execute(
                """SELECT sess.session_date, (a.id IS NOT NULL) AS attended,
                          a.checked_in_at
                   FROM sessions sess
                   LEFT JOIN attendance a
                     ON a.session_id = sess.id AND a.matricula = %s
                   ORDER BY sess.session_date DESC""",
                (matricula,),
            )
            sessions = cur.fetchall()
    finally:
        conn.close()

    return jsonify(
        {
            "matricula": matricula,
            "full_name": student["full_name"],
            "sessions": sessions,
        }
    )