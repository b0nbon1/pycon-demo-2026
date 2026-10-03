#!/usr/bin/env bash
# Run all three layers, then the triage gate. One command, every time.
set -uo pipefail
cd "$(dirname "$0")/.."
rm -rf reports artifacts; mkdir -p reports artifacts
EXTRA="${PYTEST_EXTRA:-}"
# The browser layers run in a visible Chromium window so the audience can watch.
# HEADLESS=1 ./demo/run.sh for a quick rehearsal; SLOWMO=0 to run at full speed.
BROWSER="--browser chromium"
[ "${HEADLESS:-0}" = "1" ] || BROWSER="$BROWSER --headed --slowmo ${SLOWMO:-300}"

printf '\n\033[1m── layer 1: API contract ─────────────────────────\033[0m\n'
pytest -m api  $EXTRA -q --junitxml=reports/api.xml
printf '\n\033[1m── layer 2: UI\033[0m\n'
pytest -m ui   $BROWSER $EXTRA -q --junitxml=reports/ui.xml
printf '\n\033[1m── layer 3: end-to-end across the seam\033[0m\n'
pytest -m e2e  $BROWSER $EXTRA -q --junitxml=reports/e2e.xml

printf '\n\033[1m── the gate ──────────────────────────────────────\033[0m\n'
touch changed.txt
python ai/triage.py --api-junit reports/api.xml --ui-junit reports/ui.xml \
  --e2e-junit reports/e2e.xml --diff changed.txt --no-ai
