import hashlib
import sqlite3
import time
from contextlib import closing
from functools import wraps
from pathlib import Path

from flask import abort, current_app, request

DATABASE = Path(__file__).resolve().parent.parent / "instance" / "careerpilot.sqlite3"


def _allow_request(scope, client_key, limit, window_seconds):
    window_start = int(time.time()) // window_seconds * window_seconds
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DATABASE, timeout=2)) as connection:
        with connection:
            connection.execute("CREATE TABLE IF NOT EXISTS request_limits (scope TEXT NOT NULL, client_key TEXT NOT NULL, window_start INTEGER NOT NULL, request_count INTEGER NOT NULL, PRIMARY KEY (scope, client_key, window_start))")
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT request_count FROM request_limits WHERE scope = ? AND client_key = ? AND window_start = ?",
                (scope, client_key, window_start),
            ).fetchone()
            if row and row[0] >= limit:
                return False
            connection.execute(
                "INSERT INTO request_limits (scope, client_key, window_start, request_count) VALUES (?, ?, ?, 1) "
                "ON CONFLICT(scope, client_key, window_start) DO UPDATE SET request_count = request_count + 1",
                (scope, client_key, window_start),
            )
            connection.execute("DELETE FROM request_limits WHERE window_start < ?", (window_start - window_seconds,))
    return True


def rate_limit(scope, limit, window_seconds):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            source = request.remote_addr or "unknown"
            secret = current_app.config["SECRET_KEY"]
            client_key = hashlib.sha256(f"{secret}:{source}".encode()).hexdigest()
            if not _allow_request(scope, client_key, limit, window_seconds):
                abort(429)
            return view(*args, **kwargs)
        return wrapped
    return decorate