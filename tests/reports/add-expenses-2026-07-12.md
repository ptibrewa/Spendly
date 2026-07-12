# Test Report — add-expenses

**Date:** 2026-07-12
**Spec:** `.claude/specs/07-add-expenses.md`
**Test file(s):** `tests/test_add_expense.py`

## Verdict
All green — 27 tests passed, 0 failed, 0 errored, 0 skipped (16.34s).

## From test-writer
- **Acceptance criteria covered:**
  1. Login gating on GET and POST → redirect to `/login`, no insert on anonymous POST
  2. Authed GET renders form with all 7 CATEGORIES and date prefilled to today
  3. Authed POST with valid inputs → 302 to `/profile`, exactly one matching row
  4. Empty description stored as `NULL`
  5. New expense visible on `/profile` "Recent activity"
  6. Amount validation (missing / non-numeric / 0 / negative / > 1,000,000) → "Enter a valid amount."
  7. Value preservation of category/date/description on amount failure
  8. Category validation (missing / not in CATEGORIES) → "Choose a category."
  9. Date validation (missing / bad format / future) → "Enter a valid date."
  10. Description > 500 chars → "Description is too long."
  11. Boundary cases: amount == 1,000,000; description == 500 chars; date == today (all accepted per strict inequalities)
- **Tests written:** 13 functions, parametrized out to 27 cases.
- **Spec gaps deliberately not tested:**
  - FK `IntegrityError` on invalid `user_id` — untestable via HTTP surface (session always supplies it).
  - `insert_expense()` return value — discarded by the route; would need a direct unit test.
  - Flash message content (spec makes flashing optional).
  - Presentational HTML/CSS (`.btn-primary`, `.form-error`).
  - Numeric totals increment on `/profile` — overlaps Step 05's contract.

## From test-runner
- **Passed / failed / errored / skipped:** 27 / 0 / 0 / 0
- **Failing tests with classification:** none
- **Regressions in the wider suite:** none — this is the first test file in the repo, so no prior coverage to break.

## Spec vs. implementation mismatches
None surfaced. Error messages, validation rules, and redirect behavior all match `.claude/specs/07-add-expenses.md` §3, §7, §10, §11, §12 verbatim.

## Recommended next steps
1. Commit `tests/test_add_expense.py` — Step 7 satisfies every acceptance criterion under the tested scope.
2. Optional follow-up coverage (all currently out of HTTP scope):
   - Unit test on `database.db.insert_expense` covering the FK `IntegrityError` branch and the `cursor.lastrowid` return.
   - Cross-feature test asserting `/profile` numeric totals increment after an add (currently owned by Step 05).
3. No spec ambiguities require a human decision.
4. No environment issues.

## Appendix — raw agent reports

### test-writer

Spec / acceptance criteria tested (from `.claude/specs/07-add-expenses.md` §3, §10, §11, §12):
1. Login gating on GET and POST → redirect to `/login`, no insert on anonymous POST
2. Authed GET renders form with all 7 CATEGORIES and date prefilled to today
3. Authed POST with valid inputs → 302 to `/profile`, exactly one row with matching fields
4. Empty description stored as `NULL` (§7)
5. New expense visible on `/profile` "Recent activity"
6. Amount validation: missing, non-numeric, 0, negative, > 1,000,000 → "Enter a valid amount."
7. Preserves category/date/description on amount failure
8. Category validation: missing / not in CATEGORIES → "Choose a category."
9. Date validation: missing / non-YYYY-MM-DD / future → "Enter a valid date."
10. Description > 500 chars → "Description is too long."
11. Boundary tests: amount == 1,000,000, description == 500 chars, date == today (all accepted per strict inequalities in spec)

File written: `/Users/nevergiveup/Desktop/expense-tracker/tests/test_add_expense.py` — 13 test functions, several parametrized (amount: 6 cases, category: 4 cases, date: 6 cases), totaling ~26 test cases when parametrization is expanded.

Spec-vs-implementation mismatches noticed while writing: None spotted. The implementation in `app.py` `add_expense()` closely matches the spec's error messages and rules verbatim. One minor note — the spec §5 mentions "200-char soft limit" in the textarea but §11 defines the *validation* threshold at 500 chars; test-writer tested against §11 (the validation rule) as authoritative and did not assert on the textarea's `maxlength` attribute.

Spec gaps deliberately not tested:
- FK IntegrityError on invalid `user_id` (§11) — untestable in isolation because the route always sources `user_id` from `session`; no way to submit a bogus user_id through the HTTP surface.
- `insert_expense()` return value being `cursor.lastrowid` (§4) — the route discards it, so it's not observable via the HTTP surface.
- Flash message content on success ("Expense added.") — spec §7 says "flash success (or just redirect)", so flash content is optional and not asserted.
- Exact HTML structure / CSS classes of the form (`.btn-primary`, `.form-error`) — presentational, not behavioral.
- Success case totals/count increment on `/profile` (§12 checkbox) — asserted the new description appears in Recent activity but did not diff the numeric total/count, since that overlaps with Step 05's tested behavior rather than Step 07's contract.

### test-runner

Summary
- Total: 27 tests run, 27 passed, 0 failed, 0 errored, 0 skipped
- Runtime: 16.34s
- Verdict: **all green**

Failures: None.

Regressions: None. `tests/test_add_expense.py` is the only test file; running the broader suite would yield the same 27 tests. No prior tests to regress.

Recommendations / Next steps
1. Merge / commit the new test file — the "Add expense" (Step 7) implementation satisfies every acceptance criterion the test-writer mapped from `.claude/specs/07-add-expenses.md` §3, §7, §10, §11, §12, including all boundary cases (amount == 1,000,000; description == 500 chars; date == today).
2. Consider follow-up test coverage that this batch intentionally skipped (all noted by test-writer as out of HTTP scope, but worth revisiting later):
   - Unit test on `insert_expense()` directly to cover the FK IntegrityError branch and its return value.
   - Cross-feature test verifying `/profile` numeric totals increment after add (currently owned by Step 05).
3. No spec ambiguities surfaced — nothing requires a human decision.
4. No environment issues; `venv/bin/pytest` + `pytest-flask` worked cleanly on Python 3.9.6.
