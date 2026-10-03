# The third shape of test: a FLOW that crosses the seam between the two teams.
#
# The other feature file asserts one layer at a time. This one acts in the
# browser and verifies the consequence in the API — which is the only way to
# catch a UI that renders correctly but writes the wrong thing, or an API that
# accepts a call the UI never actually makes.
#
# Keep this file small. E2E is the most expensive and flakiest layer you own;
# it earns its place only for flows where the handoff itself is the risk.

Feature: The manager ships an order from the screen

  @e2e
  Scenario: Shipping an order on screen ships that order and no other
    Given the shop manager is logged in
    And Alice has placed an order for $60
    And Bob has placed an order for $20
    When the manager clicks Ship on Alice's order
    Then the system of record shows Alice's order as shipped
    And the system of record shows Bob's order as pending
    And the screen shows Alice's order as shipped

  @e2e
  Scenario: New orders start out unshipped
    Given the shop manager is logged in
    And Alice has placed an order for $60
    Then the system of record shows Alice's order as pending
