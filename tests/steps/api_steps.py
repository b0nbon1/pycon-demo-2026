"""API-layer binding: the SAME sentences, resolved against HTTP.

Fast, deterministic, no browser. This is the gate that runs on every push.
"""

from pytest_bdd import given, when, then, parsers

from tests.conftest import MANAGER


@given("the shop manager is logged in")
def api_login(api, context_data):
    r = api.post("/api/auth/login", json=MANAGER)
    assert r.status_code == 200, r.text
    context_data["me"] = r.json()


@when(parsers.re(r"(?P<customer>\w+) places an order for \$(?P<total>[\d.]+)"))
def api_place_order(api, customer, total):
    r = api.post("/api/orders", json={"customer": customer, "total": float(total)})
    assert r.status_code == 201, r.text


def _order_for(api, customer) -> dict:
    r = api.get("/api/orders")
    assert r.status_code == 200, r.text
    mine = [o for o in r.json()["orders"] if o["customer"] == customer]
    assert mine, f"no order for {customer}"
    return mine[0]


@then(parsers.re(r"(?P<customer>\w+)'s order should ship free"))
def api_ships_free(api, customer):
    assert _order_for(api, customer)["shipping"] == 0


@then(parsers.re(r"(?P<customer>\w+)'s order should pay for shipping"))
def api_pays_shipping(api, customer):
    assert _order_for(api, customer)["shipping"] > 0


@then(parsers.re(r'(?P<customer>\w+)\'s shipping should be "(?P<shipping>free|paid)"'))
def api_shipping_is(api, customer, shipping):
    free = _order_for(api, customer)["shipping"] == 0
    assert free is (shipping == "free"), f"{customer} free={free}, expected {shipping!r}"


@then(parsers.re(r"(?P<count>\d+) orders should be listed"))
def api_order_count(api, count):
    r = api.get("/api/orders")
    assert len(r.json()["orders"]) == int(count)
