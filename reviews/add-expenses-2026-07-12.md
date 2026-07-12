# Combined Review — add-expenses (Step 7)

**Date:** 2026-07-12
**Scope:** Working-tree diff on branch `feature/add-expenses`:
- `app.py` (new `add_expense` GET/POST route, `profile()` template ctx)
- `database/db.py` (new `insert_expense`, `CATEGORIES` constant)
- `templates/add_expense.html` (new form page)
- `templates/profile.html` (inline form section)
- `static/css/style.css` (`.profile-add` + `.add-expense-form`)
- `tests/test_add_expense.py` (new)
- `.claude/specs/07-add-expenses.md` (context only)

## Verdict
- **Security:** 2 issues found — 1 MEDIUM (CSRF), 1 LOW (NaN amount), plus 1 INFO about a pre-existing weak secret default now guarding a write endpoint.
- **Code quality:** 6 issues found — 3 MEDIUM, 3 LOW, 1 INFO.
- **Overall:** **fix-before-merge.** No blockers, but the missing CSRF protection on the first real write route is worth fixing now rather than after Steps 8 and 9 add more mutating endpoints. The three MEDIUM quality issues (form duplication, error-page fallback UX, generic amount message) are also worth resolving before this merges.

## Top priorities

1. **CSRF on `POST /expenses/add`** — `app.py:255`, `templates/add_expense.html:20`, `templates/profile.html:78`. No token, no SameSite, no origin check. Fix: add Flask-WTF `CSRFProtect(app)` + `{{ csrf_token() }}` in both forms, or at minimum set `SESSION_COOKIE_SAMESITE = "Lax"` and validate `request.headers["Origin"]` in the handler.
2. **Form duplication across `add_expense.html` and `profile.html`** — the two copies already disagree (`textarea` vs `input type="text"` for description, differing `max`, differing ids, differing `autofocus`, only the standalone preserves prior POST values). Fix: extract a `templates/_add_expense_form.html` partial and `{% include %}` it from both places.
3. **Inline profile-form errors bounce to the standalone page and filter is dropped on success** — `app.py:305-317` re-renders `add_expense.html` on error (user loses stats/filter context); the redirect on success doesn't carry the `range`/`from`/`to` query args. Fix: pass a `source=profile` marker + current filter as hidden inputs, use them to route errors back to `/profile` and to rebuild the success redirect URL.
4. **Amount validation returns one generic "Enter a valid amount." for six distinct failure modes**, and the test file's `AMOUNT_MSG` locks that in — `app.py:275-280`, `tests/test_add_expense.py`. Fix: differentiate ≥0 vs. ≤1M messages, extract the `1_000_000` cap as a constant shared with the HTML `max` attribute and the tests.
5. **NaN slips through amount validation** — `float("nan")` succeeds and both `<= 0` and `> 1_000_000` return False, so NaN gets persisted and poisons downstream `SUM()`. `app.py:277-281`. Fix: `math.isfinite(amount)` guard in the same branch.
6. **Weak default `SECRET_KEY`** — `app.py:23` (pre-existing). Fix: fail closed at startup if `SPENDLY_SECRET_KEY` is unset and `debug` is False.
7. **`date` parameter shadows `datetime.date`** — `database/db.py:139`. Fix: rename to `date_iso` for consistency with `from_iso`/`to_iso` elsewhere.
8. **Unused `import sqlite3`** — `tests/test_add_expense.py:7`. Remove.
9. **`test_profile_renders_inline_add_expense_form` asserts on literal attribute strings** — brittle. Fix: parse the HTML, or drop the redundant field-name assertions (already covered by the happy-path insert test); keep the `add_pos < recent_pos` ordering check.

## Overlaps

- **`app.py:275-281` (amount validation) — flagged twice**, from different angles:
  - Security (LOW): `float("nan")` bypasses both bounds → NaN persisted.
  - Quality (MEDIUM): one generic error string for all six failure modes.
  Fixing them together — adding `math.isfinite(...)` and splitting the message per case — resolves both in one edit.
- **Form duplication + inline-form UX** (quality items 2 and 3) touch the same two templates and route. If you extract a partial (item 2), it's natural to add the `source=profile` hidden field (item 3) in the same pass.

## Human-decision items

- **CSRF strategy:** Adopt Flask-WTF now (right thing before Steps 8/9 add edit/delete), or ship a lighter SameSite + Origin check for this step and defer the full library.
- **Description control:** spec §5 currently says textarea (200-char soft limit); the inline form on `/profile` renders it as `<input type="text">`. Pick one and update whichever side is wrong.
- **Currency type:** `float` vs `Decimal` is a project-wide call. Not a blocker for this PR, but relevant if the NaN fix is treated as symptomatic of the wider "money as float" issue.

## Appendix — raw agent reports

### security-reviewer

# Security Review

**Scope:** Working tree diff for the add-expenses feature — `app.py`, `database/db.py`, `templates/profile.html`, `templates/add_expense.html`, and `static/css/style.css`. Tests/spec/report skimmed for context only.
**Verdict:** 2 issues found (1 MEDIUM, 1 LOW) plus 1 INFO about a pre-existing weakness the new POST route now amplifies.

## Findings

### [MEDIUM] New POST route has no CSRF protection
- **File:** `app.py:255` (route decorator) and `templates/profile.html:78`, `templates/add_expense.html:20` (forms)
- **Category:** csrf
- **What's wrong:** `/expenses/add` accepts `POST` and mutates per-user data based solely on the session cookie. Neither form emits a CSRF token, and the app has no CSRF middleware (`Flask-WTF` isn't in `requirements.txt`, no `@app.before_request` token check, no SameSite cookie config either — `app.secret_key` is set but `SESSION_COOKIE_SAMESITE` is not, so Flask's default is `None`, and cross-site POSTs will send the session cookie).
- **Exploit sketch:** Attacker hosts `<form action="http://victim:5001/expenses/add" method="POST">` with hidden `amount/category/date` inputs and JS auto-submit. A logged-in Spendly user visiting the page silently gets a bogus expense written to their ledger. Feasible because the route accepts standard `application/x-www-form-urlencoded` with no origin/token check.
- **Recommended fix:** Add Flask-WTF (`CSRFProtect(app)`) and `{{ csrf_token() }}` in both `add-expense-form` and the standalone template — or, at minimum, set `app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'` (blocks cross-site form POST) and validate `request.headers.get('Origin')` matches `request.host_url` inside `add_expense()`. Same fix should be rolled out to login/signup/logout/profile-filter forms, but this diff is where a state-changing write first appears.

### [LOW] `float()` amount parsing accepts NaN and writes it to the DB
- **File:** `app.py:277-281`
- **Category:** input
- **What's wrong:** `amount = float(raw_amount)` succeeds for `"nan"`, `"NaN"`, etc. NaN comparisons are always False, so both `amount <= 0` and `amount > 1_000_000` are False and validation passes. NaN is then persisted via `insert_expense`, where it will corrupt any downstream `SUM()` / analytics query.
- **Exploit sketch:** A signed-in user (or CSRF'd victim per above) submits `amount=nan`; server stores `NaN`. Every subsequent `sum_expenses` for that user returns `NaN`, poisoning their totals and top-category logic. Not a confidentiality/integrity breach beyond the user's own data, but a durable denial of the profile view for that account.
- **Recommended fix:** After `float(...)`, reject non-finite values: `import math; if not math.isfinite(amount) or amount <= 0 or amount > 1_000_000: error = "Enter a valid amount."`. Consider using `Decimal` for currency while you're there.

### [INFO] Weak default `SECRET_KEY` now guards a write endpoint
- **File:** `app.py:23`
- **Category:** secrets / auth
- **What's wrong:** `app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-only-change-me")`. Pre-existing, but until this diff the session cookie only gated read routes. Now it gates writes, so a deploy that forgets `SPENDLY_SECRET_KEY` lets anyone forge a session and post arbitrary expenses for any `user_id`.
- **Recommended fix:** Fail closed at startup if the env var is missing outside `debug=True`. E.g., `if not os.environ.get("SPENDLY_SECRET_KEY") and not app.debug: raise RuntimeError(...)`.

## Notes
- Categories checked and found clean:
  - SQL injection — `insert_expense` uses parameterized `?` placeholders correctly.
  - XSS — all templated form values (`{{ amount }}`, `{{ category }}`, `{{ description }}`, `{{ today }}`, category loop) rely on Jinja auto-escaping; no `|safe`, no `Markup`, no `render_template_string`.
  - IDOR — `user_id` comes from `session["user_id"]`, never from the form/URL.
  - Server-side length cap on `description` (500) matches the client `maxlength`.
  - Date validation rejects future dates and non-ISO strings.
  - Auth gate present (`session.get("user_id")` check redirects to login).
  - No open redirect / SSRF / subprocess usage introduced.

### code-quality-reviewer

# Code Quality Review

**Scope:** `app.py` (add_expense route + profile ctx), `database/db.py` (insert_expense, CATEGORIES), `templates/add_expense.html` (new), `templates/profile.html` (inline form), `static/css/style.css` (add-expense-form), `tests/test_add_expense.py` (new).
**Verdict:** 7 issues found (0 HIGH, 3 MEDIUM, 3 LOW, 1 INFO).

## Findings

### [MEDIUM] The add-expense form is duplicated in two templates with divergent markup
- **File:** `templates/add_expense.html` (lines 20–53) and `templates/profile.html` (lines 80–108)
- **Category:** reuse
- **What's wrong:** Both templates render the same four-field form with the same category loop, but they diverge: `textarea` vs `input type="text"` for description; different ids; only standalone has `autofocus`; only inline has `max="1000000"`; only standalone preserves prior POST values.
- **Recommended fix:** Extract the form body into a partial (e.g. `templates/_add_expense_form.html`) that accepts `categories`, `today`, and optional prior values, and `{% include %}` it from both places.

### [MEDIUM] Inline form submission from /profile drops the user onto the standalone page on validation error
- **File:** `app.py:305-317`
- **Category:** correctness / UX
- **What's wrong:** Validation failure re-renders `add_expense.html`, losing stats/filter context. Success redirects to `url_for("profile")` with no filter query args, so an active filter is silently dropped.
- **Recommended fix:** Detect a hidden `source=profile` field (or Referer), on error re-render profile with the error, on success carry the current `range`/`from`/`to` through the redirect.

### [MEDIUM] All amount validation errors return the same generic message
- **File:** `app.py:275-280`
- **Category:** readability / UX
- **What's wrong:** "Enter a valid amount." fires for six distinct failure modes; tests lock in the poor UX via a shared `AMOUNT_MSG`.
- **Recommended fix:** Differentiate ≥0 vs. ≤1M messages; extract the `1_000_000` cap to a module-level constant shared with the HTML `max` and the tests.

### [LOW] `insert_expense`'s `date` parameter shadows the imported `datetime.date` class
- **File:** `database/db.py:139`
- **Category:** readability
- **What's wrong:** Module imports `from datetime import date, timedelta`. Inside `insert_expense`, `date` refers to the string arg, not the class. Future edits reaching for `date.today()` inside this function will silently fail.
- **Recommended fix:** Rename to `date_iso` (matches `from_iso`/`to_iso` used elsewhere).

### [LOW] Unused `sqlite3` import in the new test file
- **File:** `tests/test_add_expense.py:7`
- **Recommended fix:** Remove the import.

### [LOW] `test_profile_renders_inline_add_expense_form` asserts markup details
- **File:** `tests/test_add_expense.py:258-284`
- **Category:** tests
- **What's wrong:** Asserts on literal attribute strings like `'class="add-expense-form"'`, `'action="/expenses/add"'`, `'method="POST"'`, and each `name="..."`. Ties the test to attribute ordering and duplicates coverage from other tests. The `add_pos < recent_pos` ordering check is worth keeping.
- **Recommended fix:** Parse with `html.parser`/BeautifulSoup, or drop the redundant field-name checks and keep only the positional check.

### [INFO] Amount stored as REAL is a project-wide choice
- **File:** `database/db.py`
- **What's wrong:** Not a review item for this PR, but if a future PR touches money math, note that the schema stores REAL and the app converts to float.
