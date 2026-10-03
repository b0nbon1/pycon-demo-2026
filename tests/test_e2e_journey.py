"""Binding #3 — flows that cross the seam between the two teams."""
import pytest
from pytest_bdd import scenarios

from tests.steps.e2e_steps import *  # noqa: F401,F403

pytestmark = pytest.mark.e2e

scenarios("ship_order_journey.feature")
