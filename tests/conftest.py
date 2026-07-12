"""Shared fixtures for Spendly tests.

Every test gets:
  * a fresh temp SQLite DB (via monkeypatching database.db.DATABASE)
  * a freshly-initialized schema
  * a Flask test client with a signed-in user by default (see `logged_in_client`)

We freeze "today" at 2026-07-11 for date-arithmetic tests by monkeypatching
`app.date` — the module-level `date` symbol used by `resolve_date_range`.
"""
import os
import sys
import tempfile
from datetime import date as real_date

import pytest
from werkzeug.security import generate_password_hash

# Make repo root importable regardless of where pytest is invoked from.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


FROZEN_TODAY = real_date(2026, 7, 11)


class FrozenDate(real_date):
    """Subclass of date with today() pinned to FROZEN_TODAY."""

    @classmethod
    def today(cls):
        return FROZEN_TODAY


@pytest.fixture
def frozen_today():
    return FROZEN_TODAY


@pytest.fixture
def app(monkeypatch, tmp_path):
    """Fresh Flask app bound to a fresh temp SQLite DB, with today() frozen."""
    import database.db as db_module

    tmp_db_path = str(tmp_path / "test_spendly.db")
    # Point the DB module at the temp file BEFORE importing app so the
    # module-level init_db()/seed_db() calls hit our temp DB.
    monkeypatch.setattr(db_module, "DATABASE", tmp_db_path)

    # Force a clean import of app.py so init_db()/seed_db() run against
    # the temp DB. Remove any cached module first.
    sys.modules.pop("app", None)
    import app as app_module

    # Freeze "today" for preset resolution.
    monkeypatch.setattr(app_module, "date", FrozenDate)

    # Neutralize the Step-05 auto-seed so filter tests can operate on
    # exact fixture rows without surprise inserts. Spec-relevant behavior
    # ("auto-seed only on lifetime empty") is tested separately by
    # observing seed-call side effects via a spy.
    monkeypatch.setattr(app_module, "seed_user_expenses", lambda user_id: None)

    flask_app = app_module.app
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    # Disable auto-form-CSRF etc. — we're not using Flask-WTF.

    yield flask_app

    # Cleanup: pop so next test re-imports cleanly.
    sys.modules.pop("app", None)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def app_module(app):
    """The `app` python module (not the Flask instance) — for helpers."""
    import app as app_module
    return app_module


@pytest.fixture
def db_conn(app):
    """A raw sqlite3 connection to the test DB for direct row inserts.

    Bypasses Flask's `g`-scoped connection so setup rows are visible
    to the request-scoped connection the route opens.
    """
    import sqlite3
    import database.db as db_module

    conn = sqlite3.connect(db_module.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


def _create_user(db_conn, name="Alice", email="alice@example.com", password="password123"):
    pw_hash = generate_password_hash(password, method="pbkdf2:sha256")
    cur = db_conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, pw_hash),
    )
    db_conn.commit()
    return cur.lastrowid


def _insert_expense(db_conn, user_id, amount, category, date_iso, description=""):
    db_conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date_iso, description),
    )
    db_conn.commit()


@pytest.fixture
def make_user(db_conn):
    def _make(name="Alice", email="alice@example.com", password="password123"):
        return _create_user(db_conn, name=name, email=email, password=password)
    return _make


@pytest.fixture
def add_expense(db_conn):
    def _add(user_id, amount, category, date_iso, description=""):
        _insert_expense(db_conn, user_id, amount, category, date_iso, description)
    return _add


@pytest.fixture
def signed_in_client(client, make_user, db_conn):
    """Client with a session for a fresh user. Auto-seed is neutralized
    globally by the `app` fixture, so this user has zero expenses until
    tests explicitly add them."""
    user_id = make_user()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "Alice"
    return client, user_id
