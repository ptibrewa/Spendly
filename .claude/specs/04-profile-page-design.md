# Spec Document

## 1. Overview

Replace the `/profile` placeholder in `app.py` with a real, signed-in-only profile page that displays the current user's account details **plus a lightweight snapshot of their spending** so the page never looks empty.

This step is **design-focused**: the goal is a polished, on-brand profile view that shows `name`, `email`, and `created_at` alongside a small stats row (total spent, expense count, top category) and the user's five most recent expenses. It also introduces the first **auth-gated** route in the app — visiting `/profile` while signed out must redirect to `/login`.

To keep the design honest for brand-new accounts, the route **auto-seeds 8 sample expenses for the signed-in user the first time they land on `/profile` with zero expenses on record** — reusing the shape of `seed_db()`. This guarantees the stats + recent-activity blocks always render with real data, so the design is never validated against an empty state that no returning user will actually see.

Editing the profile (name change, password change, delete account) is intentionally **out of scope** for this step; those belong in a later spec.

---

## 2. Depends on

- `01-database-setup.md` — `users` table, `get_db()`, and `PRAGMA foreign_keys = ON` must be in place.
- `02-registration.md` — accounts must be creatable so a signed-in user actually exists to view.
- `03-login-logout.md` — `session["user_id"]` / `session["user_name"]` must be populated on login; navbar must already show the **Profile / Sign out** links.

---

## 3. Routes

Replace the existing `/profile` placeholder in `app.py`.

| Method | Path | Template | Purpose |
| --- | --- | --- | --- |
| GET | `/profile` | `profile.html` | Render the signed-in user's profile card. If `session["user_id"]` is not set, redirect to `/login` with a flash. |

Behavior:

- **Auth guard**: `if not session.get("user_id"):` → `flash("Please sign in to view your profile.", "error")` and `redirect(url_for("login"))`. This is the pattern every future authenticated route will follow.
- **Fetch user**: `SELECT id, name, email, created_at FROM users WHERE id = ?` — parameterized, `session["user_id"]` as the only bind.
- **Row missing** (session references a user that no longer exists — e.g. deleted account): `session.clear()`, flash "Your session has ended. Please sign in again." with category `"error"`, redirect to `/login`. Do not render the page.
- **Empty-state seeding**: `SELECT COUNT(*) FROM expenses WHERE user_id = ?`. If the count is `0`, call `seed_user_expenses(user_id)` (new helper in `database/db.py`, see §7) before continuing. This guarantees stats + recent-activity blocks always have data — brand-new accounts, and the demo user until they add their own, both see a populated page. Seeding runs at most once per user because the check runs first.
- **Fetch stats** (all parameterized, all filtered by `user_id = ?`):
  - `total_spent` — `SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?`
  - `expense_count` — `SELECT COUNT(*) FROM expenses WHERE user_id = ?`
  - `top_category` — `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC LIMIT 1` (nullable — template handles `None`).
- **Fetch recent activity**: `SELECT amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 5`.
- On success: `render_template("profile.html", user=user, stats=stats, recent=recent)`.

---

## 4. Database Changes

No schema changes — no new tables, no altered columns, no migrations.

This step does introduce **runtime `INSERT`s** into the existing `expenses` table via the new `seed_user_expenses(user_id)` helper (see §7). The helper reuses the shape of `seed_db()` from `01-database-setup.md`: 8 expenses covering all 7 categories (one repeats), amounts and descriptions modeled on the demo seed, dates spread across the current month using `date.today().replace(day=1)` + offsets. Every insert is parameterized and tied to the passed-in `user_id`. Idempotency is enforced by the route (only called when `COUNT(*) = 0` for that user), not by the helper itself.

---

## 5. Templates

### A. `templates/profile.html` (new)

- Extends `base.html`. Fills `{% block title %}Profile — Spendly{% endblock %}` and `{% block content %}`.
- Uses the **original** design system (DM Serif Display / DM Sans, `--ink` / `--paper` / `--accent`) — profile lives with the auth/legal pages, not the v2 hero.
- Content structure (top to bottom):
  - Page header: `<h1>` "Your profile" in DM Serif Display, short DM Sans subtitle ("Your Spendly account at a glance.").
  - **Profile card** (`.profile-card`): a bordered, rounded panel with generous padding.
    - **Avatar block**: a circular monogram (first letter of `user.name`, uppercased) in accent color on paper background, ~72–96px, DM Serif Display.
    - **Details list** (`.profile-details`): a two-column key/value grid rendered as a `<dl>`:
      - "Name" → `{{ user.name }}`
      - "Email" → `{{ user.email }}`
      - "Member since" → human-formatted date from `user.created_at` (see §7 for the Jinja filter).
  - **Stats row** (`.profile-stats`): three side-by-side stat tiles, DM Sans labels in muted ink and DM Serif Display numerals in `--ink`:
    - "Total spent" → `₹{{ '%.2f'|format(stats.total_spent) }}`
    - "Expenses tracked" → `{{ stats.expense_count }}`
    - "Top category" → `{{ stats.top_category or '—' }}`
  - **Recent activity** (`.profile-recent`): a small heading "Recent activity" plus a compact list (`<ul class="recent-list">`) of the five most recent expenses. Each row shows: category chip, description (or category name if description is null), `date | humandate`, and `₹amount` right-aligned. If `recent` is empty (should not happen after seeding, but defensively), render a single "No expenses yet." row in muted ink.
  - **Actions row** (`.profile-actions`): one primary button `.btn-primary` "Sign out" pointing at `url_for("logout")`. No "Edit" button in this step — omitting it prevents dead links.
- Fully responsive. At ≤900px the stats row collapses from 3 columns to a horizontal scroll strip *or* 1-column stack (pick stack — matches the auth pages' feel). At ≤600px: avatar stacks above the details, the `<dl>` collapses to single-column, the recent-activity list rows wrap so amount drops beneath the description, and the action button becomes full-width — matching the responsive rules already used by the auth pages.

### B. `templates/base.html` (change)

- No structural changes. The existing `{% if session.user_id %}` branch already renders the **Profile** link; that link now resolves to a real page instead of a placeholder string. Verify visually — no code change expected.

### C. Other templates

- No changes to `landing.html`, `login.html`, `register.html`, `privacy.html`, `terms.html`.

---

## 6. Files to Create

- `templates/profile.html` — described in §5.A.

---

## 7. Files to Change

- `app.py`
  - Replace the `/profile` placeholder handler with the real one described in §3.
  - Import the new helper: `from database.db import get_db, init_db, seed_db, seed_user_expenses`.
  - Add a Jinja filter registered on `app` for formatting date strings. Handles both the `"YYYY-MM-DD HH:MM:SS"` shape produced by SQLite's `datetime('now')` (used for `users.created_at`) **and** the `"YYYY-MM-DD"` shape used for `expenses.date`:
    ```
    @app.template_filter("humandate")
    def humandate(value):
        from datetime import datetime
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).strftime("%B %-d, %Y")
            except ValueError:
                continue
        return value
    ```
    Used in the template as `{{ user.created_at | humandate }}` and `{{ row.date | humandate }}`. Keeps date parsing out of the template and out of the route.
- `database/db.py`
  - Add `seed_user_expenses(user_id)` — mirrors the expense-generation shape of `seed_db()` from `01-database-setup.md`: 8 rows, all 7 categories covered (one repeats), amounts and descriptions modeled on the demo seed, dates spread across the current month via `date.today().replace(day=1)` + offsets, `executemany` with parameterized SQL, single commit. Does **not** check for existing rows (that's the route's job) and does **not** touch the `users` table. Reuse the existing `date`/`timedelta` imports.
- `static/css/style.css`
  - New `/* Profile page */` banner block, added after `/* Legal pages */`.
  - Styles for:
    - `.profile-page` — page wrapper spacing.
    - `.profile-card` — bordered panel, `--paper` bg, subtle shadow, ~24–32px radius.
    - `.profile-avatar` — round, `--accent` on `--paper`, DM Serif Display letterform.
    - `.profile-details` — `<dl>` grid, DM Sans, `--ink` for values, muted ink for keys.
    - `.profile-stats` — 3-column grid on desktop, single-column stack ≤900px. Each `.stat-tile` uses `--paper` bg, subtle border, DM Sans label, DM Serif Display numeral.
    - `.profile-recent` + `.recent-list` — compact list rows; `.recent-row` uses flex layout with amount right-aligned; `.recent-chip` is a small rounded pill in `--accent` tint for the category.
    - `.profile-actions` — right-aligned on desktop, full-width on mobile.
  - Responsive rules at ≤900px (stats collapse) and ≤600px (avatar/details/list stack, button full-width) consistent with the rest of the file.

---

## 8. New Dependencies

None. `datetime` is stdlib; Flask/Jinja/Werkzeug are already installed.

---

## 9. Rules for Implementation

- Port stays **5001**. Do not change `app.run(...)`.
- Use **parameterized queries only** for the `SELECT` — never string-format `session["user_id"]` into SQL, even though it's server-controlled.
- Reuse `get_db()`; do not open a raw `sqlite3.connect` in the route.
- **Never render `password_hash`** in the template. Do not select it, do not pass it, do not log it.
- Use the **original design tokens** (`--ink`, `--paper`, `--accent`, DM Serif Display, DM Sans, `.btn-primary`) — do not introduce v2 tokens (`--sage`, Poppins, `.btn-solid`) on this page.
- Auth guard is the standard pattern for every future authenticated route: check `session.get("user_id")`, flash on failure, redirect to `/login`. Copy this shape when adding expense CRUD in later specs.
- **Empty-state seeding is per-user and one-shot**: only fire `seed_user_expenses(user_id)` when the count query returns 0 for that specific user. Do not seed on every request, do not seed for users who already have expenses (their real data must win), and do not add a "reseed" toggle. If a user later deletes all their expenses, seeding will run again the next time they visit `/profile` — that's acceptable and matches the "profile visual is always polished" goal.
- The seed helper still follows every rule from `01-database-setup.md`: parameterized SQL, REAL amounts, ISO `YYYY-MM-DD` dates, all 7 categories represented.
- The **navbar itself is not touched** — `03-login-logout.md` already handles the signed-in vs signed-out branches. Do not restyle or re-order the nav.
- Any JS added must follow the `data-*` attribute + existence-check IIFE pattern from `initVideoModal` in `static/js/main.js`. (This step is not expected to need JS.)

---

## 10. Expected Behavior

- Visiting `/profile` **while signed out** redirects to `/login`. A red flash reading "Please sign in to view your profile." is visible at the top of the login page.
- Visiting `/profile` **while signed in**:
  - Renders a page titled "Your profile".
  - Shows a circular monogram avatar with the first letter of the user's name.
  - Displays Name, Email, and "Member since" in a clean two-column layout.
  - Shows three stat tiles — Total spent, Expenses tracked, Top category — populated from the user's expenses.
  - Shows a "Recent activity" list of the five most recent expenses (category chip, description, date, amount).
  - If the user had zero expenses at page load, they now see 8 sample expenses covering all 7 categories, spread across the current month. The stats and recent-activity blocks look identical to a seasoned account's — the page never shows an empty state.
  - Users with real expenses see their own data, untouched — the seed helper only runs when the count is 0.
  - Shows a "Sign out" primary button that, when clicked, logs the user out and returns them to `/login` with the standard "You have been signed out." success flash.
- The navbar's **Profile** link (already added in `03-login-logout.md`) now leads here on every page while signed in.
- Visual style matches the auth pages (DM Serif for headings, DM Sans for body, ink/paper/accent tokens).
- On viewports ≤600px, the avatar, details, and button stack vertically without horizontal scroll.

---

## 11. Error Handling Expectations

- Signed-out access: caught by the auth guard → flash + redirect. No `abort(401)`, no 4xx.
- Session references a deleted user: session cleared, error flash, redirect to `/login`. No stack trace shown to the user.
- Malformed `created_at` value (should not happen — SQLite's `datetime('now')` produces a fixed shape, but the filter should be defensive): the `humandate` filter is allowed to raise; the debug traceback is acceptable for the teaching scaffold. Do not silently swallow the error.
- Every failure path is either an inline `error` banner on a re-rendered form or a categorized flash rendered by `base.html` — no silent failures.

---

## 12. Definition of Done

- [ ] `/profile` renders `profile.html` for signed-in users using data from parameterized `SELECT`s on `users` and `expenses`.
- [ ] `/profile` while signed out redirects to `/login` with a visible red flash.
- [ ] Session pointing at a deleted user is cleared and redirected with a visible error flash — no traceback shown.
- [ ] `password_hash` is never selected, passed, or rendered.
- [ ] `profile.html` extends `base.html`, uses the original design tokens, and matches the auth pages visually.
- [ ] Profile card shows monogram avatar, Name, Email, and human-formatted "Member since" date.
- [ ] Stats row shows Total spent, Expenses tracked, and Top category, all filtered by `user_id`.
- [ ] Recent activity list shows the five most recent expenses for the current user.
- [ ] `seed_user_expenses(user_id)` exists in `database/db.py`, inserts 8 rows covering all 7 categories with parameterized SQL, and is called from `/profile` **only** when the user's expense count is 0.
- [ ] A brand-new registered user visiting `/profile` for the first time sees a fully populated stats + recent-activity view (verified by registering a fresh account and hitting `/profile`).
- [ ] Users with existing expenses see their own data unchanged (verified by checking `COUNT(*)` before and after a `/profile` visit for the demo user).
- [ ] `humandate` Jinja filter renders both `users.created_at` and `expenses.date` formats correctly (e.g. "July 10, 2026").
- [ ] "Sign out" button on the profile page logs the user out and shows the standard flash on `/login`.
- [ ] Page is responsive at ≤900px (stats stack) and ≤600px (avatar/details/list/button stack, no horizontal scroll).
- [ ] Navbar's **Profile** link (from `03-login-logout.md`) resolves to this page on every signed-in view.
- [ ] No new pip dependencies added.
- [ ] Port is still 5001 and the app starts cleanly.
