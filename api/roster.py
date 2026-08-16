import csv
import io

from flask import Blueprint, request, jsonify

from api.db import get_connection
from api.auth import require_auth

roster_bp = Blueprint("roster", __name__)


@roster_bp.route("/api/roster", methods=["GET"])
@require_auth
def list_students():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT matricula, full_name FROM students ORDER BY full_name")
            students = cur.fetchall()
    finally:
        conn.close()
    return jsonify(students)


@roster_bp.route("/api/roster", methods=["POST"])
@require_auth
def add_student():
    """Add one student manually. Upsert -- re-adding an existing matricula
    just updates the name, doesn't error."""
    data = request.get_json(silent=True) or {}
    matricula = data.get("matricula", "").strip()
    full_name = data.get("full_name", "").strip()

    if not matricula or not full_name:
        return jsonify({"error": "missing_fields"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO students (matricula, full_name) VALUES (%s, %s)
                   ON CONFLICT (matricula) DO UPDATE SET full_name = EXCLUDED.full_name""",
                (matricula, full_name),
            )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True}), 201


@roster_bp.route("/api/roster/bulk", methods=["POST"])
@require_auth
def bulk_upload():
    """CSV upload, multipart/form-data under the field name 'file'.
    Expected columns: matricula, full_name"""
    if "file" not in request.files:
        return jsonify({"error": "missing_file"}), 400

    content = request.files["file"].stream.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    rows = []
    for row in reader:
        matricula = (row.get("matricula") or "").strip()
        full_name = (row.get("full_name") or "").strip()
        if matricula and full_name:
            rows.append((matricula, full_name))

    if not rows:
        return jsonify({"error": "no_valid_rows"}), 400

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO students (matricula, full_name) VALUES (%s, %s)
                   ON CONFLICT (matricula) DO UPDATE SET full_name = EXCLUDED.full_name""",
                rows,
            )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"ok": True, "imported": len(rows)}), 201


@roster_bp.route("/api/roster/<matricula>", methods=["DELETE"])
@require_auth
def delete_student(matricula):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM students WHERE matricula = %s", (matricula,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True})
