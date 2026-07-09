---
description: Insert N expenses for a given user over a time window
argument-hint: <user_id> <count> <period, e.g. 30d|3m|1y|this-month|last-month>
allowed-tools: Bash(venv/bin/python3:*), Read
---

Add expense rows to the SQLite database at `expense_tracker.db` using the helpers in `database/db.py`. Do NOT modify `database/db.py`.

**Arguments:** `$ARGUMENTS` — three positional values in order:

```
/seed-expenses <user_id> <count> <period>
```

1. `<user_id>` — integer, id of an existing row in `users`. If missing from the DB, print available `(id, name)` pairs and exit.
2. `<count>` — positive integer, number of expenses to insert.
3. `<period>` — window over which to spread the dates. Accepts:
   - `Nd` (e.g. `7d`, `30d`, `90d`) → last N days ending today
   - `Nm` (e.g. `1m`, `3m`, `6m`) → last N months ending today
   - `Ny` (e.g. `1y`) → last N years ending today
   - `this-month` → current calendar month
   - `last-month` → previous calendar month

If any of the three args is missing or invalid, print usage and exit 0 without inserting anything.

## Rules

- Categories (same pool `seed_db()` uses): `Food, Transport, Bills, Health, Entertainment, Shopping, Other`.
- Amounts: random float rounded to 2 decimals, with category-aware ranges (e.g. `Bills` skew higher ₹1000–₹5000, `Food`/`Transport` lower ₹50–₹800, `Shopping` ₹300–₹3000, etc.).
- Dates: random day uniformly distributed inside the resolved `<period>` window, ISO `YYYY-MM-DD`.
- Descriptions: short category-appropriate phrase from a small per-category pool (e.g. `Food` → "Groceries", "Dinner with friends", "Coffee run").

## Steps

1. Read `database/db.py` to confirm the `expenses` schema and helpers (`get_db`, `init_db`).
2. Parse the three positional args from `$ARGUMENTS`. On any parse/validation failure, print usage and exit.
3. Write a one-off script to the scratchpad that:
   - Creates a Flask app and pushes an app context.
   - Calls `init_db()` (idempotent).
   - Validates the user id: `SELECT id, name FROM users WHERE id = ?`. If missing, list available `(id, name)` pairs and exit 0.
   - Resolves `<period>` to `(start_date, end_date)` inclusive.
   - Generates `<count>` expenses (random category → category-aware amount → random date in window → random description).
   - `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)` via `executemany`.
   - Aggregates min/max date, total, and per-category `count` + `SUM(amount)` for the inserted rows.
4. Run: `venv/bin/python3 <scratchpad>/seed_expenses.py <user_id> <count> <period>`.
5. Print the confirmation summary + per-category breakdown, e.g.:

   ```
   Added 10 expense(s) for user #13 (Priya Iyer) over last 30d
   Date range: 2026-06-10 → 2026-07-08 · Total: ₹12,480.50

   ┌───────────────┬────────┬────────────┐
   │ category      │ count  │ total (₹)  │
   ├───────────────┼────────┼────────────┤
   │ Food          │ 3      │  1,240.00  │
   │ Bills         │ 2      │  6,300.00  │
   │ Transport     │ 2      │    540.50  │
   │ Shopping      │ 2      │  3,900.00  │
   │ Entertainment │ 1      │    500.00  │
   └───────────────┴────────┴────────────┘
   ```
