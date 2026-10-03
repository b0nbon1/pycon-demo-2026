"""E2E binding: act through the browser, verify in the system of record.

This is deliberately a different SHAPE from the other two bindings. The API and
UI bindings each prove one surface against the spec. This one proves the two
surfaces agree with each other — the failure mode where the screen looks right
and the database is wrong, which neither single-layer test can see.
"""

from pytest_bdd import given, when, then, parsers

from tests.conftest import MANAGER
from tests.support import locators as L


@given("the shop manager is logged in")
def e2e_login(ui_page, base_url):
    ui_page.goto(f"{base_url}/login")
    L.resolve_one(ui_page, L.EMAIL).fill(MANAGER["email"])
    L.resolve_one(ui_page, L.PASSWORD).fill(MANAGER["password"])
    L.resolve_one(ui_page, L.SUBMIT).click()
    ui_page.wait_for_url("**/orders")


@given(parsers.re(r"(?P<customer>\w+) has placed an order for \$(?P<total>[\d.]+)"))
def e2e_arrange_order(api, ui_page, customer, total):
    """Arranged via the API on purpose: the storefront is another team's app."""
    r = api.post("/api/orders", json={"customer": customer, "total": float(total)})
    assert r.status_code == 201, r.text
    ui_page.reload()


def _row_for(ui_page, customer):
    rows = L.resolve_one(ui_page, L.ORDER_LIST).get_by_test_id("order-item")
    for i in range(rows.count()):
        row = rows.nth(i)
        el = row.get_by_test_id("order-customer")
        if el.count() and el.inner_text().strip() == customer:
            return row
    raise AssertionError(f"no row on screen for {customer}")


@when(parsers.re(r"the manager clicks Ship on (?P<customer>\w+)'s order"))
def e2e_ship(ui_page, customer):
    # The page reloads only after the ship request returns, so waiting for the
    # reload guarantees the write has landed before any Then step checks it.
    with ui_page.expect_navigation():
        _row_for(ui_page, customer).get_by_test_id("ship-button").click()


@then(parsers.re(r"the system of record shows (?P<customer>\w+)'s order as (?P<state>shipped|pending)"))
def e2e_check_backend(api, customer, state):
    """The assertion that matters. The browser said it worked — did it?"""
    orders = api.get("/api/orders").json()["orders"]
    mine = [o for o in orders if o["customer"] == customer]
    assert mine, f"API has no order for {customer}"
    assert mine[0]["shipped"] is (state == "shipped"), \
        f"{customer}'s order in API: shipped={mine[0]['shipped']}, expected {state}"


@then(parsers.re(r"the screen shows (?P<customer>\w+)'s order as (?P<state>shipped|pending)"))
def e2e_check_screen(ui_page, customer, state):
    row = _row_for(ui_page, customer)
    assert row.get_by_test_id("order-status").inner_text().strip() == state
