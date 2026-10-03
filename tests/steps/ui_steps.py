"""UI-layer binding: the SAME sentences, resolved against a real browser.

Note what happens here. Placing an order has no screen in this app — customers
do it in the storefront, which another team owns. So the UI binding ARRANGES
through the API and ASSERTS through the DOM. That is not cheating; that is the
integration seam between the two teams, and it is exactly the seam that breaks
in real life.
"""

from pytest_bdd import given, when, then, parsers

from tests.conftest import MANAGER
from tests.support import locators as L


@given("the shop manager is logged in")
def ui_login(ui_page, base_url):
    ui_page.goto(f"{base_url}/login")
    L.resolve_one(ui_page, L.EMAIL).fill(MANAGER["email"])
    L.resolve_one(ui_page, L.PASSWORD).fill(MANAGER["password"])
    L.resolve_one(ui_page, L.SUBMIT).click()
    ui_page.wait_for_url("**/orders")


@when(parsers.re(r"(?P<customer>\w+) places an order for \$(?P<total>[\d.]+)"))
def ui_place_order(api, ui_page, customer, total):
    r = api.post("/api/orders", json={"customer": customer, "total": float(total)})
    assert r.status_code == 201, r.text
    ui_page.reload()


def _order_rows(ui_page) -> list[dict]:
    """Read the order table off the screen.

    We heal our way to the container, then read rows strictly inside it, so an
    empty list still means empty rather than "locator broke".
    """
    container = L.resolve_one(ui_page, L.ORDER_LIST)
    items = container.get_by_test_id("order-item")
    rows = []
    for i in range(items.count()):
        row = items.nth(i)
        customer = row.get_by_test_id("order-customer")
        if customer.count() == 0:
            continue
        rows.append({
            "customer": customer.inner_text().strip(),
            "shipping": row.get_by_test_id("order-shipping").inner_text().strip(),
        })
    return rows


def _shipping_on_screen(ui_page, customer) -> str:
    mine = [r["shipping"] for r in _order_rows(ui_page) if r["customer"] == customer]
    assert mine, f"no order on screen for {customer}"
    return mine[0]


@then(parsers.re(r"(?P<customer>\w+)'s order should ship free"))
def ui_ships_free(ui_page, customer):
    assert _shipping_on_screen(ui_page, customer) == "free"


@then(parsers.re(r"(?P<customer>\w+)'s order should pay for shipping"))
def ui_pays_shipping(ui_page, customer):
    assert _shipping_on_screen(ui_page, customer) != "free"


@then(parsers.re(r'(?P<customer>\w+)\'s shipping should be "(?P<shipping>free|paid)"'))
def ui_shipping_is(ui_page, customer, shipping):
    free = _shipping_on_screen(ui_page, customer) == "free"
    assert free is (shipping == "free")


@then(parsers.re(r"(?P<count>\d+) orders should be listed"))
def ui_order_count(ui_page, count):
    assert len(_order_rows(ui_page)) == int(count)
