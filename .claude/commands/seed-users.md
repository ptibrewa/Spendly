---
description: Insert N users with Indian names into expense_tracker.db
argument-hint: [count]
allowed-tools: Bash(venv/bin/python3:*), Read
---

Add users to the SQLite database at `expense_tracker.db` using the helpers in `database/db.py`. Do NOT modify `database/db.py`.

**Argument:** `$ARGUMENTS`
- Empty or non-numeric → insert 1 user.
- Positive integer N → insert N users.

## Rules

- Names come from this Indian-name pool (pick without replacement per invocation; if N exceeds the pool size, allow reuse):
  Aarav Sharma, Priya Iyer, Rohan Mehta, Ananya Verma, Kabir Reddy, Diya Nair, Vikram Singh, Ishita Kapoor, Arjun Malhotra, Meera Joshi, Aditya Rao, Sanya Gupta, Neel Chatterjee, Riya Bose, Karthik Menon.
- Email base = `firstname.lastname@spendly.com` (lowercased). If it already exists in `users`, append `1`, `2`, … before the `@` until unique. This is on top of the schema's `UNIQUE` constraint.
- Password = `password123`, hashed with `generate_password_hash(pw, method="pbkdf2:sha256")`.

## Steps

1. Read `database/db.py` to confirm helpers (`get_db`, `init_db`) and the `users` schema haven't changed.
2. Write a one-off script to the scratchpad that:
   - Creates a Flask app and pushes an app context (so `flask.g` works for `get_db()`).
   - Calls `init_db()` (idempotent — uses `CREATE TABLE IF NOT EXISTS`).
   - For each new user: pick a name from the pool, resolve a unique email via a `SELECT 1 FROM users WHERE email = ?` loop with incrementing suffix, then insert with `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)` and capture `lastrowid`.
   - `SELECT id, name, email, created_at FROM users WHERE id IN (...)` for the just-inserted ids.
3. Run: `venv/bin/python3 <scratchpad>/seed_users.py <count>`.
4. Print a confirmation table of every added user:

   ```
   Added 3 user(s):
   ┌────┬──────────────┬───────────────────────────┬─────────────────────┐
   │ id │ name         │ email                     │ created_at          │
   ├────┼──────────────┼───────────────────────────┼─────────────────────┤
   │ 12 │ Aarav Sharma │ aarav.sharma@spendly.com  │ 2026-07-09 15:44:02 │
   │ 13 │ Priya Iyer   │ priya.iyer@spendly.com    │ 2026-07-09 15:44:02 │
   │ 14 │ Rohan Mehta  │ rohan.mehta1@spendly.com  │ 2026-07-09 15:44:02 │
   └────┴──────────────┴───────────────────────────┴─────────────────────┘
   ```

   Then note in one sentence how many were added and flag any emails that had to be suffixed for uniqueness.
