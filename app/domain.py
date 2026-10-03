"""Shared domain — the rule BOTH teams depend on.

A change in this file can legitimately turn both gates red at once. That is the
signal the triage script keys off: two red layers means the behaviour moved.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import HTTPException

PASSWORD = "correct-horse"

FREE_SHIPPING_FROM = 50.00
SHIPPING_FEE = 4.99


@dataclass
class Order:
    customer: str
    total: float
    shipping: float
    shipped: bool = False


@dataclass
class Tenant:
    orders: list[Order] = field(default_factory=list)
    sessions: dict[str, str] = field(default_factory=dict)


STATE: dict[str, Tenant] = defaultdict(Tenant)


def tenant_of(x_tenant: str | None, cookie: str | None) -> Tenant:
    """Every request is scoped to a tenant, so the suite can run -n auto safely."""
    return STATE[x_tenant or cookie or "default"]


def place_order(t: Tenant, customer: str, total: float) -> Order:
    """Core rule: orders of $50 or more ship free."""
    if total <= 0:
        raise HTTPException(422, "order total must be positive")
    shipping = 0.0 if total >= FREE_SHIPPING_FROM else SHIPPING_FEE
    order = Order(customer=customer, total=total, shipping=shipping)
    t.orders.append(order)
    return order
