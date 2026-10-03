#!/usr/bin/env python3
"""
Change-impact triage for the BDD gate.

A red pipeline tells you *that* something broke. It does not tell you WHO owns
it or whether the right move is to fix the test or send the change back. This
script works that out by correlating three signals that a bare test report
never puts side by side:

  1. which LAYER went red (API binding vs UI binding of the same scenario)
  2. whether any locator DRIFTED (the UI moved under us)
  3. what the PR actually TOUCHED (the diff)

The rules below are deterministic — you can argue with them in code review.
The LLM is optional and runs *after* the verdict: it writes the human summary
and drafts the patch. It never decides whether to block. That separation is the
whole point; a model that both judges and explains will happily explain a
judgement it made up.

Usage:
  python ai/triage.py --api-junit reports/api.xml --ui-junit reports/ui.xml \\
      --drift artifacts/locator-drift.json --diff changed-files.txt
Exit code: 0 = merge allowed, 1 = blocked.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# Paths that tell us which team's change is in flight.
# Map changed paths to the team that owns them. Tune these for your repo —
# this table is the only part of the script that is project-specific.
API_PATHS = ("app/api.py", "app/domain.py", "api/", "services/", "schemas/")
UI_PATHS = ("app/ui.py", "web/", "ui/", "templates/", "static/", "components/")
TEST_PATHS = ("tests/", "features/")


@dataclass
class LayerResult:
    name: str
    total: int = 0
    failures: list[dict] = field(default_factory=list)

    @property
    def red(self) -> bool:
        return bool(self.failures)


def read_junit(path: str | None, name: str) -> LayerResult:
    r = LayerResult(name=name)
    if not path or not pathlib.Path(path).exists():
        return r
    root = ET.parse(path).getroot()
    for case in root.iter("testcase"):
        r.total += 1
        for kind in ("failure", "error"):
            node = case.find(kind)
            if node is not None:
                r.failures.append({
                    "test": case.get("name", "?"),
                    "kind": kind,
                    "message": (node.get("message") or "").strip()[:400],
                })
    return r


def classify_diff(files: list[str]) -> set[str]:
    owners: set[str] = set()
    for f in files:
        if any(f.startswith(p) for p in TEST_PATHS):
            owners.add("tests")
        if any(f.startswith(p) for p in UI_PATHS):
            owners.add("ui")
        if any(f.startswith(p) for p in API_PATHS):
            owners.add("api")
    return owners


@dataclass
class Verdict:
    decision: str      # BLOCK | FIX_FORWARD | WARN | PASS
    owner: str
    headline: str
    reasoning: str
    actions: list[str]

    @property
    def blocking(self) -> bool:
        return self.decision == "BLOCK"


def decide(api: LayerResult, ui: LayerResult, e2e: LayerResult,
           drift: list[dict], owners: set[str]) -> Verdict:
    drifted = [d["locator"] for d in drift]

    # Both bindings of the same sentence are red -> the behaviour itself moved.
    if api.red and ui.red:
        return Verdict(
            "BLOCK", "api-team",
            "Behaviour regression, not a test problem",
            "The same scenario fails at the API layer and the UI layer. When both "
            "bindings of one sentence go red, the rule the business agreed to has "
            "changed. No amount of selector work fixes this.",
            ["Send the PR back with the failing scenario attached.",
             "If the new behaviour is intended, the .feature file must change FIRST "
             "and be signed off, then the code.",
             "Ask for the acceptance criteria that justifies the new behaviour."],
        )

    # API red, UI green -> the UI is masking a contract break.
    if api.red and not ui.red:
        return Verdict(
            "BLOCK", "api-team",
            "API contract broke while the UI hid it",
            "The API binding is red but the screen still looks right — usually a "
            "default, a cached value, or client-side leniency papering over a bad "
            "response. This is the most expensive class of bug to find later.",
            ["Block the merge; the contract is the shared artifact.",
             "Have the UI team confirm whether they are tolerating a malformed "
             "response, and make that tolerance explicit or remove it."],
        )

    # UI red, API green -> whose fault depends on drift + diff.
    if ui.red and not api.red:
        if drifted and owners <= {"ui", "tests"}:
            return Verdict(
                "FIX_FORWARD", "qa",
                "Locator drift — the markup moved, the behaviour did not",
                f"The API proves the behaviour is intact. The UI binding failed and "
                f"{len(drifted)} locator(s) had to heal: {', '.join(drifted)}. This is "
                "test maintenance, not a product defect.",
                ["Do not block the PR on this.",
                 "Ask the UI team to add the stable test-id back — that is a one-line "
                 "change and it stops the next five failures.",
                 "Update the primary strategy in tests/support/locators.py."],
            )
        if "api" in owners:
            return Verdict(
                "BLOCK", "api-team + ui-team",
                "Integration seam broke between the two teams",
                "The API layer passes its own contract tests and the UI layer fails, "
                "while this PR touched API code. The API is self-consistent but no "
                "longer matches what the UI was built against — a contract change "
                "nobody told the other team about.",
                ["Block and get both teams in the same thread.",
                 "Decide whether the API change is additive (UI adapts) or breaking "
                 "(needs a version).",
                 "Add the seam to the shared .feature file so it cannot drift silently again."],
            )
        return Verdict(
            "BLOCK", "ui-team",
            "The screen does not render what the API returns",
            "Behaviour is correct at the API layer and wrong on screen, with no "
            "locator drift to explain it. The data is right and the rendering is not.",
            ["Block; attach the trace and screenshot from the failing scenario.",
             "This is a genuine UI defect, not a flaky test."],
        )

    # Both surfaces individually correct, but the flow across them is not.
    # This is the case no single-layer suite can ever produce, and the reason
    # the e2e binding exists at all.
    if e2e.red:
        return Verdict(
            "BLOCK", "api-team + ui-team",
            "Each surface is correct; the handoff between them is not",
            "The API binding passes its contract and the UI binding renders "
            "correctly, yet the end-to-end flow fails. The screen is doing "
            "something other than what it appears to do — an optimistic update "
            "that never lands, a wrong identifier on the write, or a call the UI "
            "never actually makes. Neither team's own tests can see this.",
            ["Block. Do not let either team close this as 'works on my layer'.",
             "Open the Playwright trace for the failing scenario — the network "
             "panel shows the request the UI really sent.",
             "Once fixed, keep the scenario: this is the class of bug that comes back."],
        )

    # Everything green, but the tests had to heal to get there.
    if drifted:
        return Verdict(
            "WARN", "qa",
            "Green, but the suite healed to get there",
            f"All scenarios passed. {len(drifted)} locator(s) fell back to a weaker "
            f"strategy: {', '.join(drifted)}. Healing buys you one release, not two — "
            "each fallback is a selector you are now trusting less than the last.",
            ["Merge is allowed.",
             "Open a follow-up to restore the primary test-id before it decays further.",
             "If the same locator heals twice, treat it as a failure instead."],
        )

    return Verdict("PASS", "-", "All scenarios green at every layer",
                   "API, UI and end-to-end bindings agree and no locators drifted.", [])


def render(v: Verdict, api: LayerResult, ui: LayerResult, e2e: LayerResult,
           drift: list[dict], files: list[str], narrative: str | None) -> str:
    icon = {"BLOCK": "🚫", "FIX_FORWARD": "🔧", "WARN": "⚠️", "PASS": "✅"}[v.decision]
    lines = [
        f"## {icon} {v.decision} — {v.headline}",
        "",
        f"**Owner:** {v.owner}",
        "",
        "| layer | scenarios | failed |",
        "| --- | --- | --- |",
        f"| API | {api.total} | {len(api.failures)} |",
        f"| UI | {ui.total} | {len(ui.failures)} |",
        f"| E2E | {e2e.total} | {len(e2e.failures)} |",
        "",
        "### Why", "", v.reasoning, "",
    ]
    if v.actions:
        lines += ["### What to do", ""] + [f"- {a}" for a in v.actions] + [""]
    if drift:
        lines += ["### Locator drift", ""]
        lines += [f"- `{d['locator']}`: `{d['primary']}` → `{d['healed_with']}`" for d in drift]
        lines.append("")
    failures = api.failures + ui.failures + e2e.failures
    if failures:
        lines += ["<details><summary>Failing scenarios</summary>", ""]
        lines += [f"- **{f['test']}** — {f['message'].splitlines()[0] if f['message'] else f['kind']}"
                  for f in failures[:15]]
        lines += ["", "</details>", ""]
    if files:
        lines += [f"_Changed paths considered: {', '.join(sorted(classify_diff(files))) or 'none recognised'}_", ""]
    if narrative:
        lines += ["### AI summary", "", narrative, "",
                  "_Model-written. The verdict above is rule-based; this section is not._"]
    return "\n".join(lines)


def ai_narrative(v: Verdict, api: LayerResult, ui: LayerResult, e2e: LayerResult,
                 drift: list[dict]) -> str | None:
    """Optional. Explains the verdict and drafts a fix. Never changes the verdict."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import httpx
    except ImportError:
        return None
    payload = {
        "verdict": v.decision, "owner": v.owner, "headline": v.headline,
        "api_failures": api.failures[:6], "ui_failures": ui.failures[:6],
        "e2e_failures": e2e.failures[:6], "drift": drift,
    }
    prompt = (
        "You are triaging a failed BDD pipeline for a reviewer who has 30 seconds.\n"
        "The verdict has already been decided by deterministic rules — do not "
        "second-guess it, argue with it, or soften it.\n"
        "Write at most 120 words: what broke, the single most likely cause, and the "
        "smallest concrete next step. If a locator drifted, name the exact test-id "
        "attribute the UI team should add. Plain prose, no headings.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"]).strip()
    except Exception as e:  # a flaky model must never break the gate
        return f"_(AI summary unavailable: {type(e).__name__})_"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-junit")
    ap.add_argument("--ui-junit")
    ap.add_argument("--e2e-junit")
    ap.add_argument("--drift", default="artifacts/locator-drift.json")
    ap.add_argument("--diff", help="file containing changed paths, one per line")
    ap.add_argument("--out", default="artifacts/triage.md")
    ap.add_argument("--no-ai", action="store_true")
    a = ap.parse_args()

    api = read_junit(a.api_junit, "api")
    ui = read_junit(a.ui_junit, "ui")
    e2e = read_junit(a.e2e_junit, "e2e")
    drift = json.loads(pathlib.Path(a.drift).read_text()) if pathlib.Path(a.drift).exists() else []
    files = (pathlib.Path(a.diff).read_text().split() if a.diff and pathlib.Path(a.diff).exists() else [])

    v = decide(api, ui, e2e, drift, classify_diff(files))
    narrative = None if a.no_ai else ai_narrative(v, api, ui, e2e, drift)
    report = render(v, api, ui, e2e, drift, files, narrative)

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print(report)

    if summary := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as fh:
            fh.write(report + "\n")
    return 1 if v.blocking else 0


if __name__ == "__main__":
    sys.exit(main())
