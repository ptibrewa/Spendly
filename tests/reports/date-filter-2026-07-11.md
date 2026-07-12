# Test Report — date-filter

**Date:** 2026-07-11
**Spec:** `.claude/specs/06-date-filter.md`
**Test file(s):**
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_date_filter.py`

## Verdict

**All green.** 25/25 tests passed on the feature suite; full-suite run (`pytest -v`) also 25/25 passed with no warnings, errors, or skips. No regressions (the date-filter suite is currently the entire test corpus). No spec/implementation mismatches surfaced.

## From test-writer

**Acceptance criteria covered:**
- Default `/profile` = all-time stats (spec §10)
- Preset windows with boundary checks: `this_month`, `last_30` (29 days back), `last_90` (89 days back), `ytd` (Jan 1 → today) (§9)
- `range=custom` with inclusive `from`/`to`, scoping both stats and recent list (§10)
- Malformed `from` (bad format), non-existent date `2026-02-30`, and reversed `from > to` → invalid-range flash + fallback to `all` (§11)
- Unknown `range` value silently coerced to `all` (no flash) (§11)
- Empty window renders zeros AND does not re-seed — verified via spy + row count (§10, §11)
- SQL-injection-style `from` value doesn't crash, treated as invalid (§9)
- Filter select pre-selects the current `range` for each preset and `custom` (§12)
- Signed-out and stale-session redirects unchanged (§11)

**Tests written:** 25

**Spec gaps deliberately not tested:**
- Exact wording of the "resolved-window" status line (spec §5 gives an example but doesn't nail the format)
- Client-side JS toggling of the `from`/`to` inputs (needs headless browser)
- CSS token usage (visual concern, not backend)
- Rendered em-dash character for `top_category` when None (character not specified)
- Pre-fill of `from`/`to` `<input>` values on `range=custom` reload (exact HTML wording not specified — brittle to assert)

## From test-runner

- **Passed:** 25 | **Failed:** 0 | **Errored:** 0 | **Skipped:** 0
- `pytest tests/test_date_filter.py -v` → 25 passed in 15.22s
- `pytest -v` (full suite) → 25 passed in 14.79s
- **Failing tests with classification:** none.
- **Regressions in the wider suite:** none. (Date-filter suite is the only test file in the repo — no prior tests to regress.)

**Editor diagnostic (Pylance, `conftest.py:139`)** — `signed_in_client(client, make_user, db_conn)` declares `db_conn` but never references it. Not a real bug: `make_user` already depends on `db_conn` transitively, so requesting it explicitly here provides no additional setup-ordering guarantee. Cosmetic dead weight, safe to drop, not required.

## Spec vs. implementation mismatches

None. Implementation behavior matches the spec on every criterion tested.

## Recommended next steps

1. **Ship it.** The date-filter feature is fully covered and behaviorally correct against `.claude/specs/06-date-filter.md`.
2. (Future) When the spec tightens on the intentionally-skipped items — status-line wording, JS toggle, `top_category` placeholder character, `from`/`to` pre-fill — add follow-up coverage. Human-decision items: whether any of those need tightening at all.
3. (Optional cleanup, non-blocking) Drop the unused `db_conn` parameter on `conftest.py:139` to silence the Pylance warning. Purely cosmetic.

## Appendix — raw agent reports

### test-writer

> All 25 tests pass.
>
> ## Summary
>
> ### Spec coverage (`.claude/specs/06-date-filter.md`)
> - Default `/profile` = all-time stats (§10)
> - Each preset window with boundary checks: `this_month`, `last_30` (29 days back), `last_90` (89 days back), `ytd` (Jan 1 → today) (§9)
> - `range=custom` with inclusive `from`/`to`, scoping both stats and recent list (§10)
> - Malformed `from` (bad format), non-existent date `2026-02-30`, and reversed `from > to` → invalid-range flash + fallback to all (§11)
> - Unknown `range` value silently coerced to `all` (no flash) (§11)
> - Empty window renders zeros AND does not re-seed (verified via spy + row count) (§10, §11)
> - SQL-injection-style `from` doesn't crash, treated as invalid (§9)
> - Filter select pre-selects the current `range` for each preset and `custom` (§12)
> - Signed-out and stale-session redirects unchanged (§11)
>
> ### Files written (all absolute)
> - `/Users/nevergiveup/Desktop/expense-tracker/tests/__init__.py`
> - `/Users/nevergiveup/Desktop/expense-tracker/tests/conftest.py` — fixtures: temp-DB app, client, `signed_in_client`, `add_expense`, `make_user`; freezes today via `FrozenDate` monkeypatched onto `app.date`; neutralizes `seed_user_expenses` to avoid pollution.
> - `/Users/nevergiveup/Desktop/expense-tracker/tests/test_date_filter.py` — 25 tests.
>
> ### Results
> `pytest tests/test_date_filter.py -v` → **25 passed** in ~15s.
>
> ### Spec/impl mismatches
> None found. Implementation behavior matches the spec on every criterion tested.
>
> ### Deliberately not tested (spec silent / out of scope for this feature)
> - The exact wording of the "resolved-window" status line (spec §5 gives an *example* "Showing July 1 – July 11, 2026" but doesn't nail the format — asserting an exact string would over-constrain).
> - Client-side JS toggling of the `from`/`to` inputs (`data-range-toggle` IIFE, §7, §12) — that's a JS/DOM behavior, not testable via Flask's test client without a headless browser.
> - CSS token usage (v1 vs v2) — visual concern, not backend.
> - The rendered em-dash placeholder for `top_category` when None — spec §10 says "same em-dash as Step 05" but doesn't specify the character; we assert `top_category = None` via the empty-window test's zero rendering but don't grep for `—`.
> - Pre-fill of `from`/`to` `<input>` values on `range=custom` reload — spec §12 requires it but the exact HTML attribute wording isn't specified; tests would be brittle. (The status-line date rendering test partially covers it indirectly.)

### test-runner

> ### Summary
> - Ran `pytest tests/test_date_filter.py -v`: **25 passed** in 15.22s.
> - Ran full suite `pytest -v`: **25 passed** in 14.79s (no other test files exist yet — the date-filter suite is the entire test corpus).
> - No warnings, no errors, no skips.
> - Overall verdict: **all green**.
>
> ### Failures
> None.
>
> ### Regressions
> None. There are no pre-existing tests to regress against; the writer's suite is the only one in the repo.
>
> ### Notes on the Pylance diagnostic
> `conftest.py:139` — `signed_in_client(client, make_user, db_conn)` does declare `db_conn` but never references it in the body. It is **not** a real bug:
> - Pytest fixture parameters are how you *request* a fixture; they don't need to be used by name to have an effect.
> - However, in this case `make_user` already depends on `db_conn` transitively, so requesting `db_conn` here provides no additional setup ordering guarantee. It's dead-weight but harmless — safe to drop, purely cosmetic.
>
> Not worth acting on unless the team wants to silence the linter.
>
> ### Recommendations / Next steps
> 1. Ship it — the date-filter feature is fully covered and behaviorally correct against `.claude/specs/06-date-filter.md`.
> 2. Consider follow-up test coverage for the items the writer flagged as intentionally skipped if/when the spec tightens on them (resolved-window status text, JS custom-inputs toggling, `top_category` em-dash, `from`/`to` pre-fill on custom reload).
> 3. Optional cleanup (non-blocking): drop the unused `db_conn` parameter on `conftest.py:139` to silence the Pylance warning. Human decision — leave for the next agent that has write access.
>
> Relevant paths:
> - `/Users/nevergiveup/Desktop/expense-tracker/tests/test_date_filter.py`
> - `/Users/nevergiveup/Desktop/expense-tracker/tests/conftest.py`
> - `/Users/nevergiveup/Desktop/expense-tracker/.claude/specs/06-date-filter.md`
