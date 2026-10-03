# This file is written to be readable by a product manager.
# It is bound TWICE: once to the API layer, once to the UI layer.
# Nothing in here mentions HTTP, selectors, or browsers — that is the whole point.

Feature: Bigger orders ship free
  As a shop owner
  I want orders of $50 or more to ship free
  So that customers have a reason to add one more thing to the basket

  Background:
    Given the shop manager is logged in

  @smoke
  Scenario: A big order ships free
    When Alice places an order for $60
    Then Alice's order should ship free

  Scenario: A small order pays for shipping
    When Bob places an order for $20
    Then Bob's order should pay for shipping

  Scenario Outline: Free shipping starts at exactly $50
    When Carol places an order for $<total>
    Then Carol's shipping should be "<shipping>"

    Examples:
      | total | shipping |
      | 49.99 | paid     |
      | 50    | free     |
      | 75    | free     |

  Scenario: Every order reaches the manager
    When Alice places an order for $60
    And Bob places an order for $20
    Then 2 orders should be listed
