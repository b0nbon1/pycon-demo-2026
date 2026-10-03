# Given, When, Then... Automated

Demo repo: BDD with Playwright and Python across an API and
a UI owned by two different teams, with AI doing the boring parts and a pipeline
gate that decides who owns a breakage.

## The app in one sentence

A tiny shop back office. Customers place orders; **orders of $50 or more ship
free**; a manager logs in, sees the orders and clicks **Ship**. That is the
whole product — small enough to explain in ten seconds, so the talk can be
about the tests.

## Setup

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
pytest -m api          # 6 passed
```

## The idea in one picture

```
   features/free_shipping.feature         features/ship_order_journey.feature
   (one file, readable by your PM)        (flows across the seam)
          |                |                          |
   api_steps.py       ui_steps.py               e2e_steps.py
          |                |                          |
   HTTP contract      real browser          act in browser, assert in API
          \                |                         /
                        ai/triage.py
             "who owns this break, and do we block?"
```

**Three shapes of test, and they are not the same test run three times.**

| layer | proves | cost | when |
| --- | --- | --- | --- |
| `-m api` | the business rule holds | <1s, no browser | every push |
| `-m ui` | the screen reflects the rule | seconds, sharded | every PR |
| `-m e2e` | the two surfaces agree with each other | slowest, keep it small | every PR |

The API and UI bindings share one feature file — same sentences, different
bodies. The e2e binding is deliberately a different shape: it acts through the
browser and asserts in the system of record, which is the only way to catch a
screen that renders correctly and writes the wrong thing. Neither team's own
tests can see that failure.

Keep e2e scenarios few. They are the most expensive and flakiest layer you own,
and they earn their place only where the handoff itself is the risk.

## Commands

| | |
| --- | --- |
| `make api` | layer 1, no browser, <1s |
| `make ui` | layer 2, headed and slowed down so you can watch |
| `make e2e` | layer 3, the cross-team flow |
| `make v2` | the UI team refactored — watch the suite heal |
| `make run` | all three layers plus the verdict |
| `./demo/break.sh behaviour\|testid\|seam` | inject a breakage |
| `./demo/restore.sh` | undo it |

## Layout

| path | what it is | who owns it |
| --- | --- | --- |
| `app/domain.py` | the rule both teams depend on | shared |
| `app/api.py` | JSON API | API team |
| `app/ui.py` | rendered screens | UI team |
| `features/` | the scenarios, in business language | PM + QA |
| `tests/steps/api_steps.py` | binding #1 | QA |
| `tests/steps/ui_steps.py` | binding #2 | QA |
| `tests/steps/e2e_steps.py` | binding #3, crosses the seam | QA |
| `demo/` | one-command breakages for the live demo | — |
| `tests/support/locators.py` | self-healing locator catalogue | QA |
| `ai/triage.py` | change-impact analysis and the merge verdict | QA |
| `ai/PROMPTS.md` | the prompts, each with its failure mode | — |
| `.github/workflows/bdd.yml` | the gate | — |

## Parallelism and isolation

Every scenario gets a random tenant id, sent as `X-Tenant` on API calls and as a
`tenant` cookie in the browser. Server state is namespaced by it. There is no
reset step, no ordering dependency, and `-n auto` is safe. Under xdist each
worker also gets its own app instance on its own port.

## Triage verdicts

| API | UI | E2E | drift | diff touched | verdict | owner |
| --- | --- | --- | --- | --- | --- | --- |
| red | red | — | — | — | **BLOCK** behaviour regression | api-team |
| red | green | — | — | — | **BLOCK** UI is masking a contract break | api-team |
| green | red | — | yes | ui/tests | **FIX_FORWARD** locator drift | qa |
| green | red | — | — | api | **BLOCK** integration seam | both teams |
| green | red | — | no | ui | **BLOCK** UI defect | ui-team |
| green | green | **red** | — | — | **BLOCK** the handoff is wrong | both teams |
| green | green | green | yes | — | **WARN** healed to get there | qa |
| green | green | green | no | — | **PASS** | — |

The sixth row is the one to dwell on. Both teams' suites are green, both teams
are certain the problem is elsewhere, and the product is broken. That row is the
entire argument for owning an e2e layer at all.

The verdict is deterministic — see `decide()`. The LLM writes the human summary
afterwards and never changes the decision.

## The five states the demo shows

| command | verdict | owner |
| --- | --- | --- |
| *(clean)* `make run` | ✅ PASS | — |
| `make v2` | ⚠️ WARN — green, but it healed | qa |
| `./demo/break.sh behaviour` | 🚫 BLOCK — behaviour regression | api-team |
| `./demo/break.sh testid` | 🔧 FIX_FORWARD — locator drift | qa |
| `./demo/break.sh seam` | 🚫 BLOCK — the handoff is wrong | both teams |

Always `./demo/restore.sh` between breakages.
