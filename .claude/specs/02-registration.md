# Spec Document

## 1. Overview

Wire up user registration end-to-end. The `/register` route currently only renders the form (GET); this step adds POST handling that validates input, hashes the password, inserts a new row into `users`, and redirects to the login page with a success message.

Every success or failure path in this step **must be visible to the user** — inline error banners on the form and flashed success messages on the redirected page. Silent failures are not acceptable.

This is the first feature that writes to the database and is the foundation for authentication ([[03-login]]) and everything that follows.

---

## 2. Depends on

- `01-database-setup.md` — `users` table, `get_db()`, and `PRAGMA foreign_keys = ON` must be in place.

---

## 3. Routes

Modify the existing `/register` route in `app.py` to handle both GET and POST.

| Method | Path | Template | Purpose |
| --- | --- | --- | --- |
| GET | `/register` | `register.html` | Render the registration form (existing behavior). |
| POST | `/register` | `register.html` (on error) | Validate form, create user, redirect to `/login` on success. |

On validation failure: re-render `register.html` with an `error` string and the previously entered `name` / `email` so the user doesn't retype them (password is never echoed back).

On success: `flash("Account created — please sign in.", "success")` and `redirect(url_for('login'))`.

---

## 4. Database Changes

No schema changes. This step performs its first `INSERT` into the existing `users` table.

Fields written per registration:

| Column | Value |
| --- | --- |
| name | Trimmed form input |
| email | Trimmed, lowercased form input |
| password_hash | `generate_password_hash(pw, method="pbkdf2:sha256")` |
| created_at | Default `datetime('now')` |

---

## 5. Templates

- `templates/register.html` — already exists and already POSTs to `/register`. Edits:
  - The `{% if error %}` block already renders the error banner; ensure the `error` variable is passed from the route on every failure path.
  - Preserve entered `name` and `email` on error via `value="{{ name or '' }}"` on those inputs. Do NOT preserve either password field.
  - Add a second password input `confirm_password` (label "Confirm password", `type="password"`, `required`) directly below the existing password field.
- `templates/base.html`
  - Add a flash-message region **above `{% block content %}`** that renders every message from `get_flashed_messages(with_categories=True)` inside a container like `<div class="flash flash-{{ category }}">…</div>`. This is what makes the "Account created" message visible on the login page (and every other page).
- No new templates.

---

## 6. Files to Create

- None.

---

## 7. Files to Change

- `app.py`
  - Import `request`, `redirect`, `url_for`, `flash` from `flask`.
  - Import `generate_password_hash` from `werkzeug.security`.
  - Import `get_db`.
  - Set `app.secret_key` (required for `flash`) — read from env var `SPENDLY_SECRET_KEY` with a dev fallback.
  - Replace the current `/register` handler with one accepting `methods=["GET", "POST"]` that implements the flow described in section 3.
- `templates/register.html`
  - Add `value="{{ name or '' }}"` / `value="{{ email or '' }}"` to the name and email inputs so they survive validation errors.
- `templates/base.html`
  - Add the flash-message region described in section 5.
- `static/css/style.css`
  - Add `.flash`, `.flash-success`, and `.flash-error` styles using the **original** design tokens (`--ink`, `--paper`, `--accent`) — success in a green tint, error in the same red used by `.auth-error`. Place these in a new `/* Flash messages */` banner block.

---

## 8. New Dependencies

- None — `werkzeug` is already installed (Flask dependency).

---

## 9. Rules for Implementation

- Port stays **5001**. Do not change `app.run(...)`.
- Use **parameterized queries only**: `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)`. Never string-format SQL.
- Hash passwords with `generate_password_hash(pw, method="pbkdf2:sha256")`. Never store plaintext.
- Normalize email to lowercase and strip whitespace on both `name` and `email` before validating or inserting.
- Uniqueness is enforced by the schema (`UNIQUE` on `email`) — catch `sqlite3.IntegrityError` and surface it as a form error ("An account with that email already exists."). Do not pre-check with a `SELECT` (racy).
- **Every outcome must be visible to the user.** No success/failure path may complete without either:
  - an inline `error` banner on the re-rendered form, or
  - a categorized flash message (`"success"` or `"error"`) rendered by `base.html`.
- Registration pages use the **original design system** (DM Serif Display / DM Sans, `--ink`/`--paper`/`--accent`, `.btn-primary`/`.btn-ghost`). Flash message styles must match — do not introduce v2 tokens here.
- Any JS added must follow the `data-*` attribute pattern with an existence-check IIFE (see `initVideoModal` in `static/js/main.js`).

---

## 10. Expected Behavior

- Visiting `/register` shows the existing form.
- Submitting a valid form:
  - Creates a new row in `users` with a hashed password.
  - Redirects to `/login`.
  - A green flash banner reading "Account created — please sign in." is visible at the top of the login page.
- Submitting an invalid form (missing field, bad email, short password, mismatched passwords, duplicate email):
  - Re-renders `/register` with a red error banner explaining the exact problem.
  - Name and email inputs stay populated; both password fields are blank.
  - No row is inserted.

---

## 11. Error Handling Expectations

Server-side validation (do not rely on HTML `required` alone). Each of the following renders an inline error banner on the form:

- Missing `name`, `email`, `password`, or `confirm_password` → "All fields are required."
- Email fails a simple regex (`^[^@\s]+@[^@\s]+\.[^@\s]+$`) → "Please enter a valid email address."
- Password shorter than 8 characters → "Password must be at least 8 characters."
- `password` != `confirm_password` → "Passwords do not match."
- Duplicate email (`sqlite3.IntegrityError` on `UNIQUE` constraint) → "An account with that email already exists."

All errors return HTTP 200 with the form re-rendered — no `abort()`, no 4xx. Every error message must be the exact string above so the user always sees a specific reason, never a generic "something went wrong". Unexpected exceptions bubble up (debug mode shows the traceback; that's fine for the teaching scaffold).

---

## 12. Definition of Done

- [ ] `/register` accepts POST and inserts into `users` with a hashed password.
- [ ] Successful registration redirects to `/login` and a green flashed success message is **visible** on that page.
- [ ] All five validation errors (missing field / bad email / short password / mismatched passwords / duplicate email) render as a visible red inline banner on the form.
- [ ] Name and email inputs preserve their values on validation error; both password fields are cleared.
- [ ] `templates/base.html` renders every flashed message (with categories) above the content block.
- [ ] `.flash-success` and `.flash-error` styles exist in `static/css/style.css` and use the original design tokens.
- [ ] `app.secret_key` is set (env var with dev fallback).
- [ ] No plaintext passwords in the database — verified by inspecting a seeded row.
- [ ] No new pip dependencies added.
- [ ] Port is still 5001 and app starts cleanly.
