"""Binding #1 — every scenario in the feature file, run against the API."""
import pytest
from pytest_bdd import scenarios

from tests.steps.api_steps import *  # noqa: F401,F403  (registers the step fixtures)

pytestmark = pytest.mark.api

scenarios("free_shipping.feature")
