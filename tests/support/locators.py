"""
Self-healing locators, the boring-and-actually-works version.

A locator is a NAME plus an ORDERED list of strategies. We take the first one
that resolves. If we had to fall back past the primary strategy, that is not a
pass and not a failure — it is *drift*, and we record it so the pipeline can
tell the UI team "you renamed something, here is the test-id you should add".

There is no LLM in this hot path. Calling a model per selector would be slow,
non-deterministic and expensive. The AI shows up *after* the run, in triage.py,
where it reads the drift log and drafts the fix. That split matters.
"""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass
from typing import Callable

ARTIFACTS = pathlib.Path(os.getenv("ARTIFACTS_DIR", "artifacts"))
DRIFT_LOG = ARTIFACTS / "locator-drift.json"

Strategy = Callable[[object], object]  # (page) -> playwright Locator


class LocatorNotFound(AssertionError):
    pass


@dataclass(frozen=True)
class Spec:
    name: str
    strategies: list[tuple[str, Strategy]]  # (human label, resolver)


def record_drift(name: str, used: str, primary: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    entries = []
    if DRIFT_LOG.exists():
        entries = json.loads(DRIFT_LOG.read_text() or "[]")
    entry = {"locator": name, "primary": primary, "healed_with": used}
    if entry not in entries:
        entries.append(entry)
    DRIFT_LOG.write_text(json.dumps(entries, indent=2))


def resolve(page, spec: Spec):
    """Return EVERY match. Use this when you mean a collection."""
    primary_label = spec.strategies[0][0]
    for index, (label, strategy) in enumerate(spec.strategies):
        try:
            loc = strategy(page)
            if loc.count() > 0:
                if index > 0:
                    record_drift(spec.name, used=label, primary=primary_label)
                return loc
        except Exception:  # a strategy that cannot even be built is just a miss
            continue
    raise LocatorNotFound(
        f"'{spec.name}' matched none of: {[s[0] for s in spec.strategies]}"
    )


def resolve_one(page, spec: Spec):
    """Return the first match. Use this when you mean one element to act on."""
    return resolve(page, spec).first


# ---- the app's locator catalogue -----------------------------------------
# Order is deliberate: contract-stable first, human-visible last.

EMAIL = Spec("email", [
    ("testid=email", lambda p: p.get_by_test_id("email")),
    ("label=Email", lambda p: p.get_by_label("Email")),
    ("css=#email", lambda p: p.locator("#email")),
])

PASSWORD = Spec("password", [
    ("testid=password", lambda p: p.get_by_test_id("password")),
    ("label=Password", lambda p: p.get_by_label("Password")),
])

# This one has no test-id in the app on purpose — it is the drift demo.
SUBMIT = Spec("submit", [
    ("testid=login-submit", lambda p: p.get_by_test_id("login-submit")),
    ("role=button name=Sign in", lambda p: p.get_by_role("button", name="Sign in")),
    ("role=button name=Log in", lambda p: p.get_by_role("button", name="Log in")),
    ("css=#submit", lambda p: p.locator("#submit")),
])

# Heal the CONTAINER, never the collection inside it.
#
# This is the most important line in the file. If you heal a collection
# directly, "the test-id was renamed" and "there are genuinely zero rows"
# produce the identical answer — zero matches — and your suite goes green on a
# broken page. Anchoring on a container that MUST exist keeps empty meaningful.
ORDER_LIST = Spec("order-list", [
    ("testid=order-list", lambda p: p.get_by_test_id("order-list")),
    ("css=.order-list", lambda p: p.locator(".order-list")),
    ("css=.orders-table", lambda p: p.locator(".orders-table")),
])
