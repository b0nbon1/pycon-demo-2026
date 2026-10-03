# Driving the agent (copy-paste for the live demo)

With `ai/mcp.json` loaded and the app running on :8000, give the agent this:

```
The app at http://127.0.0.1:8000 is a shop back office. Log in with
manager@shop.test / correct-horse. Orders are created via POST /api/orders
with {"customer": "Alice", "total": 60}.

Explore it and report back ONLY:
1. Every distinct state you can reach, including empty and error states.
2. Any element you interacted with that has no data-testid — list the exact
   attribute you'd add.
3. Three behaviours you observed that are NOT covered by features/free_shipping.feature.

Do not write test code. Do not modify files. For each behaviour in (3), tell me
what question I should ask the product owner before turning it into a scenario.
```
