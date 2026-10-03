"""Binding #2 — the SAME scenarios, run against the browser."""
import pytest
from pytest_bdd import scenarios

from tests.steps.ui_steps import *  # noqa: F401,F403

pytestmark = pytest.mark.ui

scenarios("free_shipping.feature")
