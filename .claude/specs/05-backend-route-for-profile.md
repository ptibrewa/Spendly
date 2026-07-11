# Spec Document

## 1. Overview

Wire up the backend for the profile page introduced in Step 04. Replace any placeholder for `/profile` in `app.py` with a real route that reads the signed-in user's row, computes summary stats (total spent, expense count, top category), fetches the 5 most recent expenses, and renders `templates/profile.html` with a `user`, `stats`, and `recent` payload.

This step turns the profile page from a static design into a data-driven view of the current user's spending, and adds a small helper in `database/db.py` so a first-time visitor sees meaningful numbers instead of zeros.

---

## 2. Depends on

- `.claude/specs/01-database-setup.md` — `users` / `expenses` tables and `get_db()`
- `.claude/specs/02-registration.md` — sign-up creates the row this route reads
- `.claude/specs/03-login-logout.md` — session state (`session["user_id"]`) that gates the route
- `.claude/specs/04-profile-page-design.md` — the Jinja template this route renders

---

## 3. Routes

| Method | Path | Template | Purpose |
| --- | --- | --- | --- |
| GET | `/profile` | `profile.html` | Show the signed-in user's account details, aggregate stats, and 5 most recent expenses. Redirects to `/login` with a flashed error if there is no active session or the session's `user_id` no longer resolves to a real user. |

No other routes change.

---

## 4. Database Changes

No schema changes.

One new seeding helper is added to `database/db.py`:

### A. `seed_user_expenses(user_id)`

- Inserts the same 8-expense fixture used by `seed_db()` (dates spread across the current month, one row per category, `amount` as REAL).
- Called from the `/profile` route the **first time** a user has zero expenses, so a freshly-registered account has a populated dashboard on first view.
- Uses `executemany` with parameterized SQL. No duplicate-check — the route only calls it when the user's expense count is `0`.

---

## 5. Templates

No new templates. `templates/profile.html` (created in Step 04) is now rendered with real context:

- `user` — `sqlite3.Row` with `id`, `name`, `email`, `created_at`.
- `stats` — dict with keys `total_spent` (float), `expense_count` (int), `top_category` (string or `None`).
- `recent` — list of `sqlite3.Row` with `amount`, `category`, `date`, `description`, ordered by `date DESC, id DESC`, limited to 5.

The template must render `stats.top_category` as an em-dash (or similar placeholder) when it is `None`, since a user with zero expenses has no top category.

A Jinja template filter `humandate` is available in `app.py` for formatting the `created_at` and `date` fields (`"July 3, 2026"` style). Use it wherever a raw ISO string would otherwise appear.

---

## 6. Files to Create

- None.

---

## 7. Files to Change

- `app.py`
    - Replace the placeholder `/profile` route with the real implementation described in section 10.
    - Import `seed_user_expenses` from `database.db` alongside `get_db`, `init_db`, `seed_db`.
- `database/db.py`
    - Add `seed_user_expenses(user_id)` (see section 4A).

---

## 8. New Dependencies

- None. Everything needed (`flask`, `werkzeug`, `sqlite3`) is already installed.

---

## 9. Rules for Implementation

- Flask runs on **port 5001** — do not change the `app.run(port=5001)` call.
- All SQL must be **parameterized** — never build query strings with `%` or f-strings.
- Every connection keeps `PRAGMA foreign_keys = ON` (already set in `get_db()`); do not disable it.
- `amount` stays `REAL`. Do not round or coerce to `int` in SQL — formatting is the template's job.
- The route must not trust the session blindly: if `session["user_id"]` does not match a row in `users`, clear the session and redirect to `/login` with a flashed error.
- Do not introduce an ORM or query builder.
- Use `COALESCE(SUM(amount), 0)` for `total_spent` so a brand-new user gets `0.0`, not `None`.
- "Top category" = category with the **highest summed amount**, not the highest count. Return `None` when there are no expenses.
- `recent` uses `ORDER BY date DESC, id DESC LIMIT 5` — the `id` tiebreaker keeps ordering stable when multiple expenses share a date.
- Follow the existing route style: inline handlers, no blueprints, `flash(...)` + `redirect(url_for(...))` for auth failures.

---

## 10. Expected Behavior

- Signed-out visitor to `/profile` → flashed error `"Please sign in to view your profile."` and redirect to `/login`.
- Signed-in visitor whose `user_id` no longer exists (e.g. account deleted) → session is cleared, flashed error, redirect to `/login`.
- Signed-in visitor with **zero expenses** → `seed_user_expenses(user_id)` runs once, the stat block re-queries, and the page renders with a populated total, count, top category, and recent list.
- Signed-in visitor with **existing expenses** → page renders directly with their real totals; no seeding runs.
- `stats.total_spent` is always a number (`0.0` for empty accounts).
- `stats.top_category` is `None` only if the user still has zero expenses after the seeding attempt (should not happen in normal flow).
- `recent` contains at most 5 rows, newest first.

---

## 11. Error Handling Expectations

- Missing session → redirect, do not render the template with empty context.
- Stale session (`user_id` not in `users`) → clear session, redirect, do not 500.
- Database errors (locked file, constraint failure during seeding) should bubble up as normal Flask exceptions — no silent `try/except: pass`.
- Do **not** catch `sqlite3.IntegrityError` in this route; the auto-seed only runs when the user has zero expenses, so there is nothing legitimate to swallow.

---

## 12. Definition of Done

- [x]  `GET /profile` returns the profile page for a signed-in user.
- [x]  Signed-out access flashes an error and redirects to `/login`.
- [x]  A session pointing at a missing user is cleared and redirected to `/login`.
- [x]  `stats.total_spent`, `stats.expense_count`, `stats.top_category` are computed from the DB, not hard-coded.
- [x]  `recent` shows the 5 most recent expenses, ordered by `date DESC, id DESC`.
- [x]  First-time users get a populated dashboard via `seed_user_expenses`.
- [x]  `seed_user_expenses(user_id)` exists in `database/db.py` and uses parameterized `executemany`.
- [x]  All SQL in the new code is parameterized.
- [x]  App still starts on port 5001 with no errors.
