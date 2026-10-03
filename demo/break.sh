#!/usr/bin/env bash
# Inject one of the three demo breakages. No editing files on stage.
#   ./demo/break.sh behaviour   -> the rule itself moved
#   ./demo/break.sh testid      -> the UI team renamed a test-id
#   ./demo/break.sh seam        -> the screen writes the wrong record
# Always paired with ./demo/restore.sh, which also clears the snapshot.
# Uses perl rather than sed -i so it behaves the same on macOS and Linux.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d demo/.backup ]; then
  echo "A breakage is already applied. Run ./demo/restore.sh first." >&2
  exit 1
fi
mkdir -p demo/.backup
cp app/domain.py app/ui.py demo/.backup/

case "${1:-}" in
  behaviour)
    perl -pi -e 's/^FREE_SHIPPING_FROM = 50\.00/FREE_SHIPPING_FROM = 100.00/' app/domain.py
    echo "BROKEN: free shipping now starts at \$100 instead of \$50  (app/domain.py)"
    echo "app/domain.py" > changed.txt ;;
  testid)
    # A component refactor renames several test-ids at once, which is how this
    # actually arrives. One has a fallback and heals; one does not and fails.
    perl -pi -e 's/data-testid="order-customer"/data-testid="customer-name"/; s/ data-testid="order-list"//' app/ui.py
    echo "BROKEN: order list + customer test-ids renamed  (app/ui.py)"
    echo "app/ui.py" > changed.txt ;;
  seam)
    perl -pi -e 's/onclick="ship\(\{i\}\)"/onclick="ship({i}+1)"/' app/ui.py
    echo "BROKEN: the Ship button ships the NEXT order in the list  (app/ui.py)"
    echo "app/ui.py" > changed.txt ;;
  *)
    rm -rf demo/.backup
    echo "usage: ./demo/break.sh [behaviour|testid|seam]"; exit 2 ;;
esac

if cmp -s app/domain.py demo/.backup/domain.py && cmp -s app/ui.py demo/.backup/ui.py; then
  rm -rf demo/.backup changed.txt
  echo "ERROR: the breakage did not apply — the pattern no longer matches the code." >&2
  exit 1
fi
