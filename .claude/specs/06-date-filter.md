# Spec Document

## 1. Overview

Add a date-range filter to the profile page so a signed-in user can narrow their stats and recent expenses to a specific window (e.g. "this month", "last 30 days", or a custom `from`/`to` range). The profile route computed totals over *all* expenses in Step 05; this step scopes those computations — `total_spent`, `expense_count`, `top_category`, and the `recent` list — to the selected date range, driven by query-string parameters.

This turns the profile page from a lifetime snapshot into a slice-able view of spending, and lays the groundwork for later reporting features that need the same filter surface.

---

## 2. Depends on

- `.claude/specs/01-database-setup.md` — `expenses.date` column (YYYY-MM-DD)
- `.claude/specs/03-login-logout.md` — session gate on `/profile`
- `.claude/specs/04-profile-page-design.md` — the template we extend with filter controls
- `.claude/specs/05-backend-route-for-profile.md` — the `/profile` route whose queries we scope

---

## 3. Routes

| Method | Path | Template | Purpose |
| --- | --- | --- | --- |
| GET | `/profile` | `profile.html` | Same as Step 05, but stats and recent list are scoped by optional `from`, `to`, and `range` query params. Bad/malformed dates fall back to "all time" with a flashed warning. |

No new routes. The filter is a GET query string on the existing `/profile` so the URL is shareable and back-button friendly.

**Accepted query params:**

- `range` — one of `all`, `this_month`, `last_30`, `last_90`, `ytd`, `custom`. Default `all`.
- `from` — `YYYY-MM-DD`, inclusive. Only read when `range=custom`.
- `to` — `YYYY-MM-DD`, inclusive. Only read when `range=custom`.

---

## 4. Database Changes

None. `expenses.date` is already stored as `YYYY-MM-DD` text (Step 01), which sorts and compares correctly with `BETWEEN` in SQLite.

---

## 5. Templates

No new templates. `templates/profile.html` gains a filter control block above the stats card:

- A `<form method="get" action="{{ url_for('profile') }}">` with:
  - A `<select name="range">` listing the six presets, with the current selection marked `selected`.
  - Two `<input type="date" name="from">` / `name="to">` fields, shown only when `range=custom` (toggle via a `data-range-toggle` attribute on the form and vanilla JS in `main.js`).
  - A submit button labelled "Apply".
- A small status line beneath the stats card showing the resolved window (e.g. "Showing July 1 – July 11, 2026") using the existing `humandate` filter.

The filter form uses the **v1 design tokens** (`--ink`, `--paper`, `--accent`, DM Sans / DM Serif Display) to match the rest of the profile page.

---

## 6. Files to Create

- None.

---

## 7. Files to Change

- `app.py`
  - Update the `/profile` route to parse the query params, resolve them into a concrete `(from_date, to_date)` pair, and pass the window into the DB helpers.
  - Add the resolved window (and the raw `range` value) to the template context so the form can pre-select the current choice and the status line can render the dates.
- `database/db.py`
  - Update the stats/recent queries used by `/profile` to accept optional `from_date` / `to_date` params and add a `WHERE date BETWEEN ? AND ?` clause when both are set. Keep the un-scoped path working when both are `None`.
- `templates/profile.html`
  - Add the filter form block and the resolved-window status line described in section 5.
- `static/js/main.js`
  - Add a self-invoking IIFE that toggles the visibility of the `from`/`to` inputs based on the `range` select value, guarded by an existence check on the form root (`data-range-toggle`).
- `static/css/style.css`
  - Add filter-form styles under a new `/* Profile filter */` banner. Reuse `.btn-primary` for the submit.

---

## 8. New Dependencies

- None. Date math uses `datetime` from the standard library.

---

## 9. Rules for Implementation

- Flask stays on **port 5001**.
- All SQL remains **parameterized** — the `BETWEEN` bounds go through `?` placeholders; do not interpolate dates into the query string.
- `PRAGMA foreign_keys = ON` stays on.
- Preset resolution happens in `app.py`, not in the template or the DB layer. The DB helpers only see `from_date` / `to_date` (or `None`).
- All date strings that reach SQL must be validated as `YYYY-MM-DD` (parsed with `datetime.strptime`, `%Y-%m-%d`). Invalid input → flash `"Invalid date range — showing all expenses."` and fall back to `range=all`.
- If `from > to`, treat as invalid (same flash + fallback) — do not silently swap.
- "This month" = 1st of the current month → today. "YTD" = Jan 1 of the current year → today. "Last 30/90" = today minus 29/89 days → today (inclusive on both ends, so the window is exactly 30 / 90 days).
- Use the v1 design tokens for the filter UI. Do not introduce v2 tokens (`--sage`, Poppins) on the profile page.
- Follow the existing `data-*` attribute pattern for the JS toggle. No inline `onclick`.
- The filter form must degrade gracefully with JavaScript disabled — the `from`/`to` inputs are always in the DOM; JS only hides them when `range != custom`. Server-side, they are only *read* when `range=custom`, so extra values in the URL are ignored rather than 500-ing.

---

## 10. Expected Behavior

- Visiting `/profile` with no query params → identical to Step 05 (all-time stats and the 5 most recent expenses across all dates).
- Selecting "This month" and submitting → the URL becomes `/profile?range=this_month`; stats and recent list are limited to expenses dated between the 1st of the current month and today, inclusive.
- Selecting "Custom" → the two date inputs appear, the user picks a range, submits, and the URL becomes `/profile?range=custom&from=YYYY-MM-DD&to=YYYY-MM-DD`.
- The status line under the stats card always names the resolved window (or "All time" for `range=all`).
- The dropdown reflects the current selection on page load — refresh preserves the filter.
- `stats.top_category` is `None` if the filtered window contains no expenses, and the template renders the same em-dash placeholder as Step 05.
- The auto-seed from Step 05 still runs only when the user has **zero lifetime expenses**, not zero-in-window — a filter that hides all rows must not trigger a re-seed.

---

## 11. Error Handling Expectations

- Malformed `from` or `to` (not `YYYY-MM-DD`, non-existent date like `2026-02-30`) → flash the invalid-range message, fall back to `range=all`, still render the page.
- `from > to` → same fallback.
- Unknown `range` value → treat as `all`, no flash needed (silently ignore garbage from URL tampering).
- Empty result set inside a valid window → render the page with `stats.expense_count = 0`, `stats.total_spent = 0.0`, `stats.top_category = None`, and an empty `recent` list. Do not 500 and do not re-seed.
- Session failures (missing / stale) behave exactly as Step 05.

---

## 12. Definition of Done

- [ ] `/profile` accepts `range`, `from`, `to` query params and scopes stats + recent list accordingly.
- [ ] Preset options `all`, `this_month`, `last_30`, `last_90`, `ytd`, `custom` all resolve to the correct inclusive window.
- [ ] Invalid or reversed date ranges fall back to "all time" with a flashed warning.
- [ ] Filter form pre-selects the current `range` and, for `custom`, pre-fills the `from`/`to` inputs.
- [ ] Status line under the stats card names the resolved window.
- [ ] `from`/`to` inputs toggle visibility based on `range` via a `data-range-toggle` IIFE in `main.js`.
- [ ] All new SQL is parameterized; `BETWEEN` bounds go through placeholders.
- [ ] Auto-seed does not fire based on filtered emptiness — only lifetime emptiness.
- [ ] Profile page still uses v1 design tokens; no v2 tokens introduced.
- [ ] App still starts on port 5001 with no errors.
