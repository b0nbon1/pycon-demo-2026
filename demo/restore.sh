#!/usr/bin/env bash
# Undo whatever break.sh did, and clear the snapshot so the next break takes a
# fresh one. (Keeping a stale snapshot silently reverts later edits.)
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d demo/.backup ]; then echo "Nothing to restore."; exit 0; fi
cp demo/.backup/domain.py app/domain.py
cp demo/.backup/ui.py app/ui.py
rm -rf demo/.backup changed.txt
echo "Restored."
