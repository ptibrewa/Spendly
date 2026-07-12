"""Tests for the Add Expense feature (Step 7).

Behavior contract lives in .claude/specs/07-add-expenses.md. These tests
derive from sections 3 (Routes), 10 (Expected Behavior), 11 (Error Handling
Expectations), and 12 (Definition of Done).
"""
import sqlite3

import pytest

from database.db import CATEGORIES


# --------------------------------------------------------------------- #
# Helpers                                                                #
# --------------------------------------------------------------------- #

def _count_expenses(db_conn, user_id):
    (n,) = db_conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    return n


def _fetch_expenses(db_conn, user_id):
    return db_conn.execute(
        "SELECT amount, category, date, description FROM expenses "
        "WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()


VALID_FORM = {
    "amount": "42.50",
    "category": "Food",
    "date": "2026-07-10",
    "description": "Lunch",
}


# --------------------------------------------------------------------- #
# Auth gating                                                            #
# --------------------------------------------------------------------- #

def test_anonymous_get_redirects_to_login(client):
    resp = client.get("/expenses/add")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_anonymous_post_redirects_to_login_and_inserts_nothing(client, make_user, db_conn):
    user_id = make_user()
    resp = client.post("/expenses/add", data=VALID_FORM)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    assert _count_expenses(db_conn, user_id) == 0


# --------------------------------------------------------------------- #
# GET form                                                               #
# --------------------------------------------------------------------- #

def test_authed_get_renders_form_with_categories_and_today(signed_in_client, frozen_today):
    client, _ = signed_in_client
    resp = client.get("/expenses/add")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    # All seven fixed categories from CATEGORIES must appear.
    for cat in CATEGORIES:
        assert cat in body, f"Category {cat!r} missing from add-expense form"

    # Date input should be prefilled with today (YYYY-MM-DD).
    assert frozen_today.isoformat() in body


# --------------------------------------------------------------------- #
# Happy path                                                             #
# --------------------------------------------------------------------- #

def test_valid_post_redirects_to_profile_and_inserts_row(signed_in_client, db_conn):
    client, user_id = signed_in_client
    resp = client.post("/expenses/add", data=VALID_FORM)

    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]

    rows = _fetch_expenses(db_conn, user_id)
    assert len(rows) == 1
    row = rows[0]
    assert float(row["amount"]) == 42.50
    assert row["category"] == "Food"
    assert row["date"] == "2026-07-10"
    assert row["description"] == "Lunch"


def test_empty_description_stored_as_null(signed_in_client, db_conn):
    client, user_id = signed_in_client
    data = dict(VALID_FORM, description="")
    resp = client.post("/expenses/add", data=data)
    assert resp.status_code == 302

    rows = _fetch_expenses(db_conn, user_id)
    assert len(rows) == 1
    assert rows[0]["description"] is None


def test_new_expense_appears_on_profile_recent(signed_in_client, db_conn):
    client, user_id = signed_in_client
    data = dict(VALID_FORM, description="Uniquely-Recognizable-Purchase-XYZ")
    post_resp = client.post("/expenses/add", data=data)
    assert post_resp.status_code == 302

    resp = client.get("/profile")
    assert resp.status_code == 200
    assert "Uniquely-Recognizable-Purchase-XYZ" in resp.get_data(as_text=True)


# --------------------------------------------------------------------- #
# Validation — amount                                                    #
# --------------------------------------------------------------------- #

AMOUNT_MSG = "Enter a valid amount."


@pytest.mark.parametrize(
    "bad_amount",
    ["", "abc", "0", "-5", "1000000.01", "2000000"],
    ids=["missing", "nonnumeric", "zero", "negative", "just_over_cap", "way_over_cap"],
)
def test_invalid_amount_rerenders_with_error(signed_in_client, db_conn, bad_amount):
    client, user_id = signed_in_client
    data = dict(VALID_FORM, amount=bad_amount)
    resp = client.post("/expenses/add", data=data)

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert AMOUNT_MSG in body
    assert _count_expenses(db_conn, user_id) == 0


def test_invalid_amount_preserves_other_fields(signed_in_client):
    client, _ = signed_in_client
    data = {
        "amount": "abc",
        "category": "Transport",
        "date": "2026-07-05",
        "description": "Bus ticket",
    }
    resp = client.post("/expenses/add", data=data)
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Previously submitted values re-rendered so the user isn't retyping.
    assert "Transport" in body
    assert "2026-07-05" in body
    assert "Bus ticket" in body


# --------------------------------------------------------------------- #
# Validation — category                                                  #
# --------------------------------------------------------------------- #

CATEGORY_MSG = "Choose a category."


@pytest.mark.parametrize(
    "bad_category",
    ["", "Bogus", "food", "FOOD"],
    ids=["missing", "not_in_list", "wrong_case_lower", "wrong_case_upper"],
)
def test_invalid_category_rerenders_with_error(signed_in_client, db_conn, bad_category):
    client, user_id = signed_in_client
    data = dict(VALID_FORM, category=bad_category)
    resp = client.post("/expenses/add", data=data)

    assert resp.status_code == 200
    assert CATEGORY_MSG in resp.get_data(as_text=True)
    assert _count_expenses(db_conn, user_id) == 0


# --------------------------------------------------------------------- #
# Validation — date                                                      #
# --------------------------------------------------------------------- #

DATE_MSG = "Enter a valid date."


@pytest.mark.parametrize(
    "bad_date",
    ["", "notadate", "07/10/2026", "2026-13-01", "2027-01-01", "2026-07-12"],
    ids=["missing", "garbage", "wrong_format", "invalid_month", "far_future", "tomorrow"],
)
def test_invalid_date_rerenders_with_error(signed_in_client, db_conn, bad_date):
    client, user_id = signed_in_client
    data = dict(VALID_FORM, date=bad_date)
    resp = client.post("/expenses/add", data=data)

    assert resp.status_code == 200
    assert DATE_MSG in resp.get_data(as_text=True)
    assert _count_expenses(db_conn, user_id) == 0


# --------------------------------------------------------------------- #
# Validation — description length                                        #
# --------------------------------------------------------------------- #

DESC_MSG = "Description is too long."


def test_description_over_500_chars_rerenders_with_error(signed_in_client, db_conn):
    client, user_id = signed_in_client
    data = dict(VALID_FORM, description="x" * 501)
    resp = client.post("/expenses/add", data=data)

    assert resp.status_code == 200
    assert DESC_MSG in resp.get_data(as_text=True)
    assert _count_expenses(db_conn, user_id) == 0


def test_description_exactly_500_chars_is_accepted(signed_in_client, db_conn):
    """Spec §11 says '>500' fails — the boundary at 500 should succeed."""
    client, user_id = signed_in_client
    data = dict(VALID_FORM, description="x" * 500)
    resp = client.post("/expenses/add", data=data)

    assert resp.status_code == 302
    assert _count_expenses(db_conn, user_id) == 1


# --------------------------------------------------------------------- #
# Boundary — amount at cap of 1,000,000                                  #
# --------------------------------------------------------------------- #

def test_amount_at_upper_cap_is_accepted(signed_in_client, db_conn):
    """Spec §11 says '> 1,000,000' fails — exactly 1,000,000 should succeed."""
    client, user_id = signed_in_client
    data = dict(VALID_FORM, amount="1000000")
    resp = client.post("/expenses/add", data=data)

    assert resp.status_code == 302
    assert _count_expenses(db_conn, user_id) == 1


def test_date_equal_to_today_is_accepted(signed_in_client, db_conn, frozen_today):
    """Spec §11 says 'in the future' fails — today itself should succeed."""
    client, user_id = signed_in_client
    data = dict(VALID_FORM, date=frozen_today.isoformat())
    resp = client.post("/expenses/add", data=data)

    assert resp.status_code == 302
    assert _count_expenses(db_conn, user_id) == 1


# --------------------------------------------------------------------- #
# Inline add-expense form on /profile (spec §5, §10, §12)                #
# --------------------------------------------------------------------- #

def test_profile_renders_inline_add_expense_form(signed_in_client, frozen_today):
    """Spec §5 & §12: /profile must render the inline add-expense form,
    positioned above the Recent activity section, wired to POST /expenses/add,
    with the four fields and today prefilled on the date input."""
    client, _ = signed_in_client
    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    assert 'class="add-expense-form"' in body
    assert 'action="/expenses/add"' in body
    assert 'method="POST"' in body

    assert 'name="amount"' in body
    assert 'name="category"' in body
    assert 'name="date"' in body
    assert 'name="description"' in body

    for category in CATEGORIES:
        assert f'value="{category}"' in body

    assert f'value="{frozen_today.isoformat()}"' in body

    add_pos = body.find('class="add-expense-form"')
    recent_pos = body.find('class="profile-recent"')
    assert add_pos != -1 and recent_pos != -1
    assert add_pos < recent_pos, "Inline add form must appear above Recent activity"
