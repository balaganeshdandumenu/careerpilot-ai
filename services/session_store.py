import json
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

DATABASE = Path(__file__).resolve().parent.parent / "instance" / "careerpilot.sqlite3"
SESSION_TTL = 24 * 60 * 60


def _connect():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    with connection:
        connection.execute("CREATE TABLE IF NOT EXISTS career_sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL, expires_at INTEGER NOT NULL)")
    return connection


def load_career_data(session):
    session_id = session.get("career_session_id")
    if not session_id:
        return {}
    now = int(time.time())
    with closing(_connect()) as connection:
        with connection:
            row = connection.execute("SELECT data FROM career_sessions WHERE id = ? AND expires_at > ?", (session_id, now)).fetchone()
            connection.execute("DELETE FROM career_sessions WHERE expires_at <= ?", (now,))
    if not row:
        session.pop("career_session_id", None)
        return {}
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return {}


def save_career_data(session, data):
    session_id = session.get("career_session_id") or uuid.uuid4().hex
    session["career_session_id"] = session_id
    with closing(_connect()) as connection:
        with connection:
            connection.execute(
                "INSERT INTO career_sessions (id, data, expires_at) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data, expires_at = excluded.expires_at",
                (session_id, json.dumps(data, separators=(",", ":")), int(time.time()) + SESSION_TTL),
            )