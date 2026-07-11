import os
import re
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db, seed_user_expenses

app = Flask(__name__)
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-only-change-me")

with app.app_context():
    init_db()
    seed_db()


@app.template_filter("humandate")
def humandate(value):
    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%B %-d, %Y")
        except ValueError:
            continue
    return value


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

    (expense_count,) = db.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?",
        (user["id"],),
    ).fetchone()

    if expense_count == 0:
        seed_user_expenses(user["id"])
        (expense_count,) = db.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?",
            (user["id"],),
        ).fetchone()

    row = db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?",
        (user["id"],),
    ).fetchone()
    total_spent = float(row["total"])

    row = db.execute(
        "SELECT category FROM expenses WHERE user_id = ? "
        "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user["id"],),
    ).fetchone()
    top_category = row["category"] if row else None

    recent = db.execute(
        "SELECT amount, category, date, description FROM expenses "
        "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 5",
        (user["id"],),
    ).fetchall()

    stats = {
        "total_spent": total_spent,
        "expense_count": expense_count,
        "top_category": top_category,
    }
    return render_template("profile.html", user=user, stats=stats, recent=recent)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
