# The AI half

Three places a model earns its keep here, and a fourth where it does not.

Each prompt is paired with its failure mode. Read both. A prompt you cannot
describe the failure mode of is a prompt you are not ready to put in a pipeline.

---

## 1. User story → Gherkin

Used once per story, by a human, in a chat window. Not in CI.

```
You are writing acceptance criteria for a team that will automate them directly.

Rules:
- Declarative, not imperative. Write what the system must be true of, never how
  the user clicks. "Given the shop manager is logged in" — never "Given I
  navigate to /login and type into #email".
- Every noun in a Then must be observable at BOTH the API and the UI layer.
  If it can only be seen on screen, say so explicitly and I will split it out.
- No step may mention a selector, a URL, an HTTP verb, or a status code.
- Prefer a Scenario Outline when the only thing changing is a value.
- Maximum 5 scenarios. If the story needs more, the story is too big — say so
  instead of writing them.
- Output only the .feature file. No commentary.

User story:
<paste here>

Existing step vocabulary (reuse these exact sentences wherever they fit):
<paste the output of `pytest --generate-missing` or your steps file>
```

**Where it fails:** it invents plausible-sounding business rules to fill gaps.
Asked for "free shipping on bigger orders", it will confidently pick a threshold
nobody agreed to. It cannot know that $50 and not $40 is the cutoff, or whether
$50.00 exactly counts — that came from finance, a meeting, or an argument. Every generated scenario
needs a human to confirm the *numbers*, even when the prose reads perfectly.
This is the single highest-risk step in the whole workflow, because a wrong
scenario that passes is worse than no scenario at all.

---

## 2. Gherkin → step definitions

```
Write pytest-bdd step definitions for the scenarios below.

- Use parsers.re with named groups. Articles vary ("a"/"an") — handle both.
- Steps receive fixtures: `api` (httpx.Client), `ui_page` (Playwright Page),
  `context_data` (dict shared across one scenario).
- Do not write assertions inside When steps. Arrange in Given, act in When,
  assert only in Then.
- Never use sleeps. Never use XPath. Never use nth-child.
- For the UI layer, resolve elements through tests/support/locators.py only.

Scenarios:
<paste>
```

**Where it fails:** it reaches for `time.sleep()` and brittle CSS chains the
moment it cannot see the DOM, and it will happily write a `When` step that
asserts. Both are cheap to catch in review, which is why this step is
low-risk — the tests either bind or they don't, and you find out in seconds.

---

## 3. Failure triage (`triage.py`)

The model writes the summary. **It does not decide whether to block.** The
verdict comes from deterministic rules you can read in `decide()` and argue with
in code review.

**Where it fails:** if you let it judge, it rationalises. Give a model a red
pipeline and ask "should we merge?" and it will produce a fluent, confident
paragraph in either direction depending on how you phrased the question. Rules
decide; models narrate. Keep that boundary and the pipeline stays trustworthy on
the day everyone is tired and shipping at 5pm on a Friday.

---

## 4. Exploration via Playwright MCP

Point an agent at the running app and let it click around and propose scenarios.
See `ai/mcp.json`. This is genuinely good at finding states you forgot: empty
lists, error banners, the second page of results.

**Where it fails:** it proposes tests for what the app *does*, which is not the
same as what the app *should* do. It will faithfully write a scenario locking in
your bug. Treat MCP output as a list of questions for the product owner, never
as tests to commit. Run it against a branch, read the diff, throw most of it
away.

---

## The rule that ties these together

AI writes the *draft* and the *explanation*. Humans and deterministic code own
the *decisions* — what the rule is, and whether it ships. Every time a team wires
this the other way round, the suite becomes a thing nobody trusts and everybody
re-runs until it goes green.
