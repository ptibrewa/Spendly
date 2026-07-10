import os
import re
import sqlite3

from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-only-change-me")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
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


@app.route("/login")
def login():
    return render_template("login.html")


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
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
