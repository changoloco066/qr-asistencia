"""One-off script to create the teacher account (there's only ever one, for now).
Run once, locally, with DATABASE_URL pointing at the same DB the app uses.

Usage:
    DATABASE_URL=postgresql://... python scripts/seed_teacher.py <username> <password>
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from werkzeug.security import generate_password_hash
from api.db import get_connection


def main():
    if len(sys.argv) != 3:
        print("Usage: python seed_teacher.py <username> <password>")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    password_hash = generate_password_hash(password)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teachers (username, password_hash) VALUES (%s, %s)",
                (username, password_hash),
            )
        conn.commit()
    finally:
        conn.close()

    print(f"Teacher '{username}' created.")


if __name__ == "__main__":
    main()
