#!/bin/bash
#
# Machine Vision Flow - Log Viewer
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"

print_banner "Machine Vision Flow - Logs" "$BLUE"

show_log() {
    local file="$1"
    local label="$2"

    if [ -f "$file" ]; then
        echo -e "${YELLOW}Showing ${label} log:${NC}"
        tail -f "$file"
    else
        echo "${label} log not found"
    fi
}

case "${1:-all}" in
    backend|python)
        show_log "$BACKEND_LOG_FILE" "Python backend"
        ;;
    node-red|nodered)
        show_log "$NODE_RED_LOG_FILE" "Node-RED"
        ;;
    clear)
        echo "Clearing log files..."
        : >"$BACKEND_LOG_FILE" 2>/dev/null || true
        : >"$NODE_RED_LOG_FILE" 2>/dev/null || true
        echo "Log files cleared"
        ;;
    *)
        echo -e "${YELLOW}Following all logs (Ctrl+C to exit)...${NC}"
        echo
        touch "$BACKEND_LOG_FILE" "$NODE_RED_LOG_FILE"
        if command -v multitail >/dev/null 2>&1; then
            multitail -i "$BACKEND_LOG_FILE" -i "$NODE_RED_LOG_FILE"
        else
            tail -f "$BACKEND_LOG_FILE" "$NODE_RED_LOG_FILE" 2>/dev/null | while IFS= read -r line; do
                case "$line" in
                    *"$BACKEND_LOG_FILE"*)
                        echo -e "${BLUE}[BACKEND]${NC} $line"
                        ;;
                    *"$NODE_RED_LOG_FILE"*)
                        echo -e "${YELLOW}[NODE-RED]${NC} $line"
                        ;;
                    *)
                        echo "$line"
                        ;;
                esac
            done
        fi
        ;;
esac
