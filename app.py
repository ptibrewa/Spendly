import os
import re
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    CATEGORIES,
    count_expenses,
    get_db,
    init_db,
    insert_expense,
    recent_expenses,
    seed_db,
    seed_user_expenses,
    sum_expenses,
    top_category_for,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-only-change-me")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

with app.app_context():
    init_db()
    seed_db()


@app.template_filter("humandate")
def humandate(value):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%B %-d, %Y")
        except ValueError:
            continue
    return value


VALID_RANGES = {"all", "this_month", "last_30", "last_90", "ytd", "custom"}


def _parse_iso(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def resolve_date_range(range_key, raw_from, raw_to):
    today = date.today()

    if range_key not in VALID_RANGES:
        range_key = "all"

    if range_key == "all":
        return None, None, "all", None

    if range_key == "this_month":
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat(), "this_month", None

    if range_key == "last_30":
        start = today - timedelta(days=29)
        return start.isoformat(), today.isoformat(), "last_30", None

    if range_key == "last_90":
        start = today - timedelta(days=89)
        return start.isoformat(), today.isoformat(), "last_90", None

    if range_key == "ytd":
        start = today.replace(month=1, day=1)
        return start.isoformat(), today.isoformat(), "ytd", None

    # range_key == "custom"
    try:
        start = _parse_iso(raw_from or "")
        end = _parse_iso(raw_to or "")
    except ValueError:
        return None, None, "all", "Invalid date range — showing all expenses."

    if start > end:
        return None, None, "all", "Invalid date range — showing all expenses."

    return start.isoformat(), end.isoformat(), "custom", None


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not name or not email or not password or not confirm_password:
        error = "All fields are required."
    elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif password != confirm_password:
        error = "Passwords do not match."
    else:
        error = None

    if error:
        return render_template("register.html", error=error, name=name, email=email)

    pw_hash = generate_password_hash(password, method="pbkdf2:sha256")
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, pw_hash),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return render_template(
            "register.html",
            error="An account with that email already exists.",
            name=name,
            email=email,
        )

    flash("Account created — please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not email or not password:
        return render_template("login.html", error="All fields are required.", email=email)

    db = get_db()
    user = db.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email)

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("landing"))


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy.html")


@app.route("/terms-and-conditions")
def terms_and_conditions():
    return render_template("terms.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))

    db = get_db()
    user = db.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()

    if user is None:
        session.clear()
        flash("Your session has ended. Please sign in again.", "error")
        return redirect(url_for("login"))

    (lifetime_count,) = db.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?",
        (user["id"],),
    ).fetchone()

    if lifetime_count == 0:
        seed_user_expenses(user["id"])

    from_iso, to_iso, resolved_range, range_error = resolve_date_range(
        request.args.get("range", "all"),
        request.args.get("from"),
        request.args.get("to"),
    )
    if range_error:
        flash(range_error, "error")

    stats = {
        "total_spent": sum_expenses(user["id"], from_iso, to_iso),
        "expense_count": count_expenses(user["id"], from_iso, to_iso),
        "top_category": top_category_for(user["id"], from_iso, to_iso),
    }
    recent = recent_expenses(user["id"], from_iso, to_iso)

    date_filter = {
        "range": resolved_range,
        "from_iso": from_iso,
        "to_iso": to_iso,
    }

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        recent=recent,
        date_filter=date_filter,
        categories=CATEGORIES,
        today=date.today().isoformat(),
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        flash("Please sign in to view analytics.", "error")
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        flash("Please sign in to add an expense.", "error")
        return redirect(url_for("login"))

    today_iso = date.today().isoformat()

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            today=today_iso,
        )

    raw_amount = (request.form.get("amount") or "").strip()
    category = (request.form.get("category") or "").strip()
    raw_date = (request.form.get("date") or "").strip()
    description = (request.form.get("description") or "").strip()

    error = None
    amount = None
    date_iso = None

    try:
        amount = float(raw_amount)
        if amount <= 0 or amount > 1_000_000:
            error = "Enter a valid amount."
    except ValueError:
        error = "Enter a valid amount."

    if not error and category not in CATEGORIES:
        error = "Choose a category."

    if not error:
        try:
            parsed = datetime.strptime(raw_date, "%Y-%m-%d").date()
            if parsed > date.today():
                error = "Enter a valid date."
            else:
                date_iso = parsed.isoformat()
        except ValueError:
            error = "Enter a valid date."

    if not error and len(description) > 500:
        error = "Description is too long."

    if error:
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            today=today_iso,
            error=error,
            amount=raw_amount,
            category=category,
            date=raw_date,
            description=description,
        )

    insert_expense(
        session["user_id"],
        amount,
        category,
        date_iso,
        description or None,
    )
    flash("Expense added.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
