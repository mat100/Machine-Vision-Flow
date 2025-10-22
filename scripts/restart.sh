#!/bin/bash
#
# Machine Vision Flow - Restart Script
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Restarting Machine Vision Flow..."
echo

"$SCRIPT_DIR/stop.sh"
echo
sleep 2
"$SCRIPT_DIR/start.sh" $@