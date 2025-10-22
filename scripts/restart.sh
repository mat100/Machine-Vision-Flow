#!/bin/bash
#
# Machine Vision Flow - Restart Script
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"

print_banner "Restarting Machine Vision Flow" "$BLUE"

"$SCRIPT_DIR/stop.sh"
sleep 2
"$SCRIPT_DIR/start.sh" "$@"
