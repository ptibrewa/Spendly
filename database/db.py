import sqlite3
from datetime import date, timedelta

from flask import g
from werkzeug.security import generate_password_hash

DATABASE = "expense_tracker.db"


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    db.commit()


def seed_db():
    db = get_db()

    (existing,) = db.execute("SELECT COUNT(*) FROM users").fetchone()
    if existing >= 1:
        return

    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (
            "Demo User",
            "demo@spendly.com",
            generate_password_hash("demo123", method="pbkdf2:sha256"),
        ),
    )
    user_id = cursor.lastrowid

    today = date.today()
    first = today.replace(day=1)

    def d(offset):
        return (first + timedelta(days=offset)).isoformat()

    sample_expenses = [
        (user_id,  450.00, "Food",          d(1),  "Groceries for the week"),
        (user_id,  120.00, "Transport",     d(3),  "Metro card recharge"),
        (user_id, 1800.00, "Bills",         d(5),  "Electricity bill"),
        (user_id,  800.00, "Health",        d(8),  "Pharmacy — monthly meds"),
        (user_id,  350.00, "Entertainment", d(12), "Movie night"),
        (user_id, 2200.00, "Shopping",      d(15), "New running shoes"),
        (user_id,   90.00, "Other",         d(18), "Notebook and pens"),
        (user_id,  260.00, "Food",          d(22), "Dinner with friends"),
    ]

    db.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        sample_expenses,
    )
    db.commit()


def seed_user_expenses(user_id):
    db = get_db()

    today = date.today()
    first = today.replace(day=1)

    def d(offset):
        return (first + timedelta(days=offset)).isoformat()

    sample_expenses = [
        (user_id,  450.00, "Food",          d(1),  "Groceries for the week"),
        (user_id,  120.00, "Transport",     d(3),  "Metro card recharge"),
        (user_id, 1800.00, "Bills",         d(5),  "Electricity bill"),
        (user_id,  800.00, "Health",        d(8),  "Pharmacy — monthly meds"),
        (user_id,  350.00, "Entertainment", d(12), "Movie night"),
        (user_id, 2200.00, "Shopping",      d(15), "New running shoes"),
        (user_id,   90.00, "Other",         d(18), "Notebook and pens"),
        (user_id,  260.00, "Food",          d(22), "Dinner with friends"),
    ]

    db.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        sample_expenses,
    )
    db.commit()
