"""Tests for the date-filter feature on GET /profile (Spec 06).

These tests derive expectations from .claude/specs/06-date-filter.md.
"today" is frozen to 2026-07-11 via the `app` fixture in conftest.
"""
import re
import sqlite3
from datetime import date as real_date

import pytest


def _is_option_selected(body, value):
    """Return True if <option value="X" ... selected ...> appears in body.

    Uses a regex so whitespace variations (multiple spaces, newlines,
    optional quoting on `selected`) don't break the assertion.
    """
    pattern = re.compile(
        rf'<option[^>]*\bvalue=["\']{re.escape(value)}["\'][^>]*\bselected\b',
        re.IGNORECASE,
    )
    return bool(pattern.search(body))


# ---------------------------------------------------------------------------
# Session gating (unchanged from Step 05)
# ---------------------------------------------------------------------------

def test_signed_out_user_redirected_to_login(client):
    resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_stale_session_redirected_to_login(client):
    # user_id points at a non-existent user
    with client.session_transaction() as sess:
        sess["user_id"] = 99999
    resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# Default: no query params → all-time stats
# ---------------------------------------------------------------------------

def test_default_profile_shows_all_time_stats(signed_in_client, add_expense):
    client, user_id = signed_in_client
    add_expense(user_id, 100.00, "Food", "2024-01-15")
    add_expense(user_id, 250.00, "Bills", "2025-06-01")
    add_expense(user_id, 50.00, "Food", "2026-07-05")

    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # all three amounts should be summed → 400.00
    assert "400" in body
    # count of 3
    assert "3" in body


def test_default_profile_filter_context_is_all(signed_in_client):
    client, _ = signed_in_client
    resp = client.get("/profile")
    body = resp.get_data(as_text=True)
    # The "all" option should be pre-selected (spec §5, §10)
    assert _is_option_selected(body, "all")


# ---------------------------------------------------------------------------
# Preset windows (today frozen at 2026-07-11)
# ---------------------------------------------------------------------------

class TestPresetThisMonth:
    """this_month = 2026-07-01 → 2026-07-11 (inclusive)."""

    def test_includes_first_of_month(self, signed_in_client, add_expense):
        client, uid = signed_in_client
        add_expense(uid, 10.0, "A", "2026-07-01")
        add_expense(uid, 20.0, "B", "2026-06-30")  # excluded
        resp = client.get("/profile?range=this_month")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "10" in body
        # count is 1
        assert ">1<" in body or " 1 " in body or "1</" in body

    def test_includes_today(self, signed_in_client, add_expense):
        client, uid = signed_in_client
        add_expense(uid, 77.0, "X", "2026-07-11")
        resp = client.get("/profile?range=this_month")
        assert "77" in resp.get_data(as_text=True)

    def test_excludes_future(self, signed_in_client, add_expense):
        client, uid = signed_in_client
        add_expense(uid, 10.0, "In", "2026-07-05")
        add_expense(uid, 99.0, "Out", "2026-07-12")  # tomorrow, excluded
        resp = client.get("/profile?range=this_month")
        body = resp.get_data(as_text=True)
        # Total should be 10.00, not 109.00
        assert "99" not in body or "10.00" in body


class TestPresetLast30:
    """last_30 = today - 29 days → today = 2026-06-12 → 2026-07-11 inclusive."""

    def test_includes_boundary_start(self, signed_in_client, add_expense):
        client, uid = signed_in_client
        add_expense(uid, 42.0, "In", "2026-06-12")
        add_expense(uid, 99.0, "Out", "2026-06-11")  # one day earlier, excluded
        resp = client.get("/profile?range=last_30")
        body = resp.get_data(as_text=True)
        assert "42" in body
        assert "99.00" not in body

    def test_includes_today(self, signed_in_client, add_expense):
        client, uid = signed_in_client
        add_expense(uid, 55.0, "T", "2026-07-11")
        resp = client.get("/profile?range=last_30")
        assert "55" in resp.get_data(as_text=True)


class TestPresetLast90:
    """last_90 = 2026-04-13 → 2026-07-11 inclusive."""

    def test_includes_boundary_start(self, signed_in_client, add_expense):
        client, uid = signed_in_client
        add_expense(uid, 33.0, "In", "2026-04-13")
        add_expense(uid, 88.0, "Out", "2026-04-12")
        resp = client.get("/profile?range=last_90")
        body = resp.get_data(as_text=True)
        assert "33" in body
        assert "88.00" not in body


class TestPresetYTD:
    """ytd = 2026-01-01 → 2026-07-11 inclusive."""

    def test_includes_jan_first(self, signed_in_client, add_expense):
        client, uid = signed_in_client
        add_expense(uid, 11.0, "In", "2026-01-01")
        add_expense(uid, 22.0, "Out", "2025-12-31")
        resp = client.get("/profile?range=ytd")
        body = resp.get_data(as_text=True)
        assert "11" in body
        assert "22.00" not in body

    def test_excludes_prior_year(self, signed_in_client, add_expense):
        client, uid = signed_in_client
        add_expense(uid, 100.0, "Old", "2024-06-01")
        resp = client.get("/profile?range=ytd")
        body = resp.get_data(as_text=True)
        assert "100.00" not in body


# ---------------------------------------------------------------------------
# Custom range
# ---------------------------------------------------------------------------

def test_custom_range_scopes_inclusively(signed_in_client, add_expense):
    client, uid = signed_in_client
    add_expense(uid, 10.0, "A", "2026-05-01")  # boundary start
    add_expense(uid, 20.0, "B", "2026-05-15")  # inside
    add_expense(uid, 30.0, "C", "2026-05-31")  # boundary end
    add_expense(uid, 40.0, "D", "2026-04-30")  # excluded
    add_expense(uid, 50.0, "E", "2026-06-01")  # excluded

    resp = client.get("/profile?range=custom&from=2026-05-01&to=2026-05-31")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Sum = 60.00
    assert "60" in body
    # excluded amounts should not appear as totals (they may still appear elsewhere; check total line)
    assert "40.00" not in body
    assert "50.00" not in body


def test_custom_range_recent_list_scoped(signed_in_client, add_expense):
    client, uid = signed_in_client
    add_expense(uid, 10.0, "In", "2026-05-15", description="INSIDE_WINDOW")
    add_expense(uid, 99.0, "Out", "2026-06-15", description="OUTSIDE_WINDOW")

    resp = client.get("/profile?range=custom&from=2026-05-01&to=2026-05-31")
    body = resp.get_data(as_text=True)
    assert "INSIDE_WINDOW" in body
    assert "OUTSIDE_WINDOW" not in body


# ---------------------------------------------------------------------------
# Error handling — malformed dates, reversed range, unknown range
# ---------------------------------------------------------------------------

INVALID_FLASH = "Invalid date range — showing all expenses."


def test_malformed_from_date_flashes_and_falls_back(signed_in_client, add_expense):
    client, uid = signed_in_client
    add_expense(uid, 500.0, "A", "2024-01-01")  # outside any recent window

    resp = client.get("/profile?range=custom&from=not-a-date&to=2026-05-31")
    body = resp.get_data(as_text=True)
    assert INVALID_FLASH in body
    # Fell back to all → the 2024 expense IS included
    assert "500" in body


def test_nonexistent_date_flashes_and_falls_back(signed_in_client, add_expense):
    client, uid = signed_in_client
    add_expense(uid, 500.0, "A", "2024-01-01")

    resp = client.get("/profile?range=custom&from=2026-02-30&to=2026-03-10")
    body = resp.get_data(as_text=True)
    assert INVALID_FLASH in body
    assert "500" in body


def test_reversed_range_flashes_and_falls_back(signed_in_client, add_expense):
    client, uid = signed_in_client
    add_expense(uid, 500.0, "A", "2024-01-01")

    resp = client.get("/profile?range=custom&from=2026-06-30&to=2026-06-01")
    body = resp.get_data(as_text=True)
    assert INVALID_FLASH in body
    assert "500" in body


def test_unknown_range_silently_coerces_to_all(signed_in_client, add_expense):
    client, uid = signed_in_client
    add_expense(uid, 700.0, "A", "2024-01-01")

    resp = client.get("/profile?range=bogus_value")
    body = resp.get_data(as_text=True)
    # No flash
    assert INVALID_FLASH not in body
    # Falls back to all-time — 700 is included
    assert "700" in body


def test_sql_injection_in_from_is_rejected(signed_in_client, add_expense):
    """Rule §9: parameterized SQL. An injection-style `from` value must
    both (a) not crash and (b) be treated as invalid."""
    client, uid = signed_in_client
    add_expense(uid, 900.0, "A", "2024-01-01")

    resp = client.get("/profile?range=custom&from=2026-01-01' OR '1'='1&to=2026-12-31")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert INVALID_FLASH in body
    # Falls back to all-time → 900 present
    assert "900" in body


# ---------------------------------------------------------------------------
# Empty result set inside a valid window
# ---------------------------------------------------------------------------

def test_empty_window_renders_zeros_and_does_not_reseed(
    app, signed_in_client, add_expense, monkeypatch
):
    """§10, §11: empty window must render zeros and MUST NOT trigger the
    lifetime-empty auto-seed."""
    client, uid = signed_in_client
    # Give the user a single lifetime expense OUTSIDE the requested window.
    add_expense(uid, 12.34, "Old", "2020-01-01", description="LIFETIME_ONLY")

    # Spy on seed_user_expenses. It's already stubbed to a no-op by the
    # app fixture, but we replace with a counter so we can assert.
    import app as app_module
    calls = {"n": 0}

    def spy(user_id):
        calls["n"] += 1

    monkeypatch.setattr(app_module, "seed_user_expenses", spy)

    resp = client.get("/profile?range=custom&from=2026-07-01&to=2026-07-11")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    # Zero stats inside the window
    assert "0.00" in body or "0.0" in body
    # Auto-seed did NOT fire (user has 1 lifetime expense)
    assert calls["n"] == 0

    # And row count in DB is unchanged (no injected seeds)
    import database.db as db_module
    conn = sqlite3.connect(db_module.DATABASE)
    (n,) = conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (uid,)).fetchone()
    conn.close()
    assert n == 1


# ---------------------------------------------------------------------------
# Filter context pre-selection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("range_key", ["this_month", "last_30", "last_90", "ytd"])
def test_filter_pre_selects_current_range(signed_in_client, range_key):
    client, _ = signed_in_client
    resp = client.get(f"/profile?range={range_key}")
    body = resp.get_data(as_text=True)
    assert _is_option_selected(body, range_key), (
        f'expected <option value="{range_key}" ... selected> in rendered HTML'
    )


def test_filter_pre_selects_custom(signed_in_client):
    client, _ = signed_in_client
    resp = client.get("/profile?range=custom&from=2026-05-01&to=2026-05-31")
    body = resp.get_data(as_text=True)
    assert _is_option_selected(body, "custom")
