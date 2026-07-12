# Spec Document

## 1. Overview

Replace the placeholder `"Add expense — coming in Step 7"` at `GET /expenses/add` with a working form that lets a logged-in user record a new expense (amount, category, date, optional description) and persist it to the `expenses` table.

This step turns Spendly from a read-only demo into an actual tracker — it's the first write path a real user exercises, and every later feature (edit, delete, analytics) assumes rows land here first.

The same form is also embedded inline on `/profile` (above the "Recent activity" section) so the common case — a user glancing at their profile and jotting an expense — doesn't require navigating to a separate page. Both entry points POST to the same `/expenses/add` handler.

---

## 2. Depends on

- `01-database-setup.md` — `expenses` table, `get_db()`, fixed category list
- `02-registration.md` — user accounts exist
- `03-login-logout.md` — session-based auth so we know which `user_id` the expense belongs to
- `05-backend-route-for-profile.md` — profile page is where the user lands after adding an expense

---

## 3. Routes

Two changes in `app.py`, both replacing the current placeholder at line 251:

| Method | Path | Renders | Purpose |
| --- | --- | --- | --- |
| GET | `/expenses/add` | `add_expense.html` | Show the empty add-expense form |
| POST | `/expenses/add` | redirect to `/profile` on success, re-render form with errors on failure | Validate + insert one row into `expenses` |

Both must require login — if `session["user_id"]` is missing, redirect to `/login`.

---

## 4. Database Changes

None. Schema from `01-database-setup.md` already has every column this feature needs (`user_id`, `amount`, `category`, `date`, `description`, `created_at`).

A new helper function is added to `database/db.py`:

### `insert_expense(user_id, amount, category, date, description)`

- Parameterized `INSERT INTO expenses (...)`
- `description` may be `None`
- Returns the new row's `id` (via `cursor.lastrowid`)
- Caller is responsible for validation — this function trusts its inputs

---

## 5. Templates

### `templates/add_expense.html` (new)

- Extends `base.html`
- Fills `{% block title %}` → `Add Expense — Spendly`
- Fills `{% block content %}` → a single centered form card
- Form: `method="POST"` to `/expenses/add`
- Fields:
  - `amount` — `<input type="number" step="0.01" min="0.01" required>`
  - `category` — `<select required>` populated from the fixed category list in `01-database-setup.md` (Food, Transport, Bills, Health, Entertainment, Shopping, Other)
  - `date` — `<input type="date" required>`, defaults to today
  - `description` — `<textarea>` (optional, 200-char soft limit)
- Submit button uses `.btn-primary` (v1 tokens — this is not a landing page)
- Above the fields, render `{% if error %}<p class="form-error">{{ error }}</p>{% endif %}`
- On validation failure, re-render with previously submitted values so the user isn't retyping

### `templates/profile.html` (change)

- Add a new `<section class="profile-add">` **above** `<section class="profile-recent">`.
- Section contains a `<form class="add-expense-form" method="POST" action="{{ url_for('add_expense') }}">` with the same four fields as `add_expense.html` (amount, category, date, description) using `.form-group` / `.form-input` and a `.btn-primary` submit.
- Fields rely on HTML5 constraints (`required`, `step`, `min`, `max`, `type="date"` with `max="{{ today }}"`, `maxlength="500"`) for client-side hints; the server still validates identically.
- No inline error surface on the profile form — on validation failure the shared `/expenses/add` handler falls back to rendering `add_expense.html` with the error (acceptable, uncommon path).
- The `profile()` view must pass `categories=CATEGORIES` and `today=date.today().isoformat()` to the template.

---

## 6. Files to Create

- `templates/add_expense.html` — the form described in section 5

---

## 7. Files to Change

- `app.py`:
  - Remove placeholder body of `add_expense()` at line 252
  - Accept both `GET` and `POST` via `methods=["GET", "POST"]`
  - Require login (redirect to `/login` if `session["user_id"]` missing)
  - On `POST`: read form fields, validate, call `insert_expense(...)`, flash success (or just redirect), `return redirect(url_for("profile"))`
  - Import `insert_expense` from `database.db`
  - Import `redirect`, `url_for`, `flash` if not already imported
- `database/db.py`:
  - Add `insert_expense(...)` per section 4
  - Add a module-level `CATEGORIES` tuple with the seven fixed strings from `01-database-setup.md`, so both the template `<select>` and the server validator share one source of truth.
- `templates/profile.html`:
  - Add the inline `<section class="profile-add">` described in section 5, positioned above `.profile-recent`.
- `app.py` — `profile()`:
  - Pass `categories=CATEGORIES` and `today=date.today().isoformat()` to `render_template("profile.html", ...)`.
- `static/css/style.css`:
  - Add `.profile-add` (mirrors `.profile-recent` card treatment) and `.add-expense-form` (2-column grid on desktop, single column below 700px).

---

## 8. New Dependencies

None. Stdlib + already-installed packages cover it.

---

## 9. Rules for Implementation

- Flask serves on **port 5001** — don't touch `app.run(...)`.
- **Parameterized SQL only** — no f-strings, no `%` formatting inside the query.
- `PRAGMA foreign_keys = ON` is already set by `get_db()`; an invalid `user_id` must raise, not silently insert.
- Store `amount` as `REAL` (parse via `float(...)`), store `date` as `YYYY-MM-DD` string exactly as the `<input type="date">` submits.
- Category value must be one of the seven fixed strings from `01-database-setup.md` — validate server-side, don't trust the `<select>`.
- Use v1 design tokens (`--ink`, `--paper`, `--accent`, `.btn-primary`) — this is not landing-page v2 territory.
- No new JS unless the form genuinely needs it; if you add any, follow the `data-*` attribute pattern documented in `CLAUDE.md`.
- Login-gate the route with the same pattern already used by `/profile`.

---

## 10. Expected Behavior

- Logged-in user visits `/expenses/add` → sees the form with `date` prefilled to today.
- Logged-in user visits `/profile` → sees the same four-field form inline (above "Recent activity"), with `date` prefilled to today and the "Choose a category" placeholder selected.
- Fills valid amount, category, date, optional description → submits (from either entry point) → row inserted → redirected to `/profile` where the new expense appears in "Recent activity" and increments the count/total.
- Anonymous user visits `/expenses/add` → redirected to `/login`.
- Form re-renders with an inline error on any validation failure, preserving the values the user already typed. (The inline profile form falls back to `add_expense.html` on the rare server-side validation failure — HTML5 constraints prevent most of these client-side.)

---

## 11. Error Handling Expectations

Server-side validation must reject and surface a message for each of:

- `amount` missing, non-numeric, `<= 0`, or `> 1,000,000` — "Enter a valid amount."
- `category` missing or not in the fixed list — "Choose a category."
- `date` missing, not `YYYY-MM-DD`, or in the future — "Enter a valid date."
- `description` longer than 500 characters — "Description is too long." (soft-cap; DB has no length constraint)

Foreign-key violations (invalid `user_id`) should propagate as `sqlite3.IntegrityError` — this shouldn't happen in practice because we take `user_id` from the session, but don't catch and swallow.

---

## 12. Definition of Done

- [ ] `GET /profile` renders the inline add-expense form above the "Recent activity" section for logged-in users.
- [ ] Submitting the inline profile form inserts the row and returns the user to `/profile` (same handler as `/expenses/add`).
- [ ] `GET /expenses/add` renders the form for logged-in users, redirects anonymous users to `/login`.
- [ ] `POST /expenses/add` inserts a row and redirects to `/profile` on success.
- [ ] `insert_expense(...)` exists in `database/db.py` and uses parameterized SQL.
- [ ] All four validation cases in section 11 render the form with an inline error and preserve submitted values.
- [ ] Category `<select>` is populated from the fixed list; server also validates against that list.
- [ ] New expense appears in `/profile` "Recent expenses" and is counted in totals for the current date filter.
- [ ] No new pip dependencies; no changes to `app.run(...)`.
- [ ] Manual smoke: log in as demo user → add one expense per category → all seven appear on `/profile`.
