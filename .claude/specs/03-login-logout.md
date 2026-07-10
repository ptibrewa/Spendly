# Spec Document

## 1. Overview

Wire up login and logout end-to-end. The `/login` route currently only renders the form (GET) and `/logout` is a placeholder string; this step adds POST handling for `/login` that validates credentials against the `users` table, establishes a server-side session, and redirects to a landing area for signed-in users. `/logout` clears the session and redirects to `/login` with a success flash.

Every success or failure path in this step **must be visible to the user** — inline error banners on the form and flashed messages on the redirected page. Silent failures are not acceptable.

This is the first feature that reads authenticated state and lays the foundation for [[04-profile]] and every route that will need a logged-in user thereafter.

---

## 2. Depends on

- `01-database-setup.md` — `users` table, `get_db()`, and `PRAGMA foreign_keys = ON` must be in place.
- `02-registration.md` — accounts must be creatable, `app.secret_key` must already be configured, and `base.html` must already render flashed messages.

---

## 3. Routes

Modify the existing `/login` route in `app.py` to handle both GET and POST, and replace the `/logout` placeholder with a real handler.

| Method | Path | Template | Purpose |
| --- | --- | --- | --- |
| GET | `/login` | `login.html` | Render the sign-in form. If `session["user_id"]` is already set, redirect to `/` instead. |
| POST | `/login` | `login.html` (on error) | Validate credentials, set `session["user_id"]`, redirect to `/` on success. If already signed in, redirect to `/` without processing. |
| GET | `/logout` | — | Clear the session and redirect to `/login` with a success flash. |

Also modify the existing `/register` route (from `02-registration.md`) to redirect to `/` when `session["user_id"]` is already set — a signed-in user should never see the registration form. Apply the same guard to both GET and POST.

On validation failure: re-render `login.html` with an `error` string and the previously entered `email` so the user doesn't retype it (password is never echoed back).

On success: `session["user_id"] = user["id"]`, `session["user_name"] = user["name"]`, then `redirect(url_for("landing"))`.

On logout: `session.clear()`, `flash("You have been signed out.", "success")`, `redirect(url_for("login"))`.

---

## 4. Database Changes

No schema changes. This step performs its first authenticated `SELECT` against the existing `users` table:

```
SELECT id, name, password_hash FROM users WHERE email = ?
```

---

## 5. Templates

- `templates/login.html` — already exists and already POSTs to `/login`. Edits:
  - The `{% if error %}` block already renders the error banner; ensure the `error` variable is passed from the route on every failure path.
  - Preserve the entered `email` on error via `value="{{ email or '' }}"` on that input. Do NOT preserve the password field.
- `templates/base.html`
  - Update the navbar so it shows **Sign in / Create account** when `session.user_id` is not set, and **Profile / Sign out** when it is. The sign-out link points to `url_for("logout")`. Use the existing navbar markup and original design tokens — do not restyle the navbar.
- No new templates.

---

## 6. Files to Create

- None.

---

## 7. Files to Change

- `app.py`
  - Import `session` from `flask`.
  - Import `check_password_hash` from `werkzeug.security`.
  - Replace the current `/login` handler with one accepting `methods=["GET", "POST"]` that implements the flow described in section 3. Both methods must short-circuit to `redirect(url_for("landing"))` if `session.get("user_id")` is already set.
  - Add the same signed-in guard to the existing `/register` handler: if `session.get("user_id")` is set, redirect to `/` before rendering the form or processing a POST.
  - Replace the `/logout` placeholder with a real handler that clears the session and redirects to `/login`.
- `templates/login.html`
  - Add `value="{{ email or '' }}"` to the email input so it survives validation errors.
- `templates/base.html`
  - Add the conditional navbar links described in section 5.

---

## 8. New Dependencies

- None — `werkzeug` is already installed (Flask dependency) and Flask's `session` is part of the core.

---

## 9. Rules for Implementation

- Port stays **5001**. Do not change `app.run(...)`.
- Use **parameterized queries only**: `SELECT ... WHERE email = ?`. Never string-format SQL.
- Verify passwords with `check_password_hash(user["password_hash"], password)`. Never compare hashes with `==` or reimplement the check.
- Normalize email to lowercase and strip whitespace before querying (must match how `02-registration.md` stored it).
- **Never reveal which field was wrong.** Whether the email doesn't exist or the password is wrong, surface the same generic error — "Invalid email or password." — to avoid leaking which accounts exist.
- **Every outcome must be visible to the user.** No success/failure path may complete without either:
  - an inline `error` banner on the re-rendered form, or
  - a categorized flash message (`"success"` or `"error"`) rendered by `base.html`.
- Login/logout pages use the **original design system** (DM Serif Display / DM Sans, `--ink`/`--paper`/`--accent`, `.btn-primary`/`.btn-ghost`). Do not introduce v2 tokens here.
- Sessions rely on `app.secret_key` set in `02-registration.md`. Do not hard-code a new secret.
- Any JS added must follow the `data-*` attribute pattern with an existence-check IIFE (see `initVideoModal` in `static/js/main.js`).

---

## 10. Expected Behavior

- Visiting `/login` when signed out shows the existing form. Visiting `/login` **while already signed in** redirects straight to `/` — the form never appears.
- Visiting `/register` while already signed in likewise redirects to `/` — a signed-in user is never asked to create another account.
- Clicking the navbar's **Sign in / Create account** links is impossible when signed in, because the navbar renders **Profile / Sign out** instead (see section 5).
- Submitting valid credentials:
  - Sets `session["user_id"]` and `session["user_name"]`.
  - Redirects to `/` (the landing page).
  - Navbar now shows **Profile / Sign out** on every page.
- Submitting invalid credentials (unknown email OR wrong password):
  - Re-renders `/login` with a red error banner reading "Invalid email or password."
  - Email input stays populated; password is blank.
  - Session remains empty.
- Visiting `/logout` (whether signed in or not):
  - Clears the session.
  - Redirects to `/login`.
  - A green flash banner reading "You have been signed out." is visible at the top of the login page.
  - Navbar reverts to **Sign in / Create account**.

---

## 11. Error Handling Expectations

Server-side validation (do not rely on HTML `required` alone). Each of the following renders an inline error banner on the form:

- Missing `email` or `password` → "All fields are required."
- Email doesn't match any row **or** password hash check fails → "Invalid email or password." (single generic message covering both cases).

All errors return HTTP 200 with the form re-rendered — no `abort()`, no 4xx. Every error message must be the exact string above. Unexpected exceptions bubble up (debug mode shows the traceback; that's fine for the teaching scaffold).

---

## 12. Definition of Done

- [ ] `/login` accepts POST, verifies the password hash, and populates `session["user_id"]` on success.
- [ ] Successful login redirects to `/`.
- [ ] Both credential failures (unknown email / wrong password) render the same generic red banner: "Invalid email or password."
- [ ] Missing-field submissions render "All fields are required." as an inline red banner.
- [ ] Email input preserves its value on validation error; the password field is cleared.
- [ ] `/logout` clears the session and redirects to `/login` with a green flashed "You have been signed out." message visible on that page.
- [ ] Navbar in `base.html` shows **Sign in / Create account** when logged out and **Profile / Sign out** when logged in.
- [ ] Visiting `/login` or `/register` while already signed in redirects to `/` (verified for both GET and POST).
- [ ] Session survives page navigation (verified by loading multiple pages after signing in).
- [ ] No new pip dependencies added.
- [ ] Port is still 5001 and app starts cleanly.
