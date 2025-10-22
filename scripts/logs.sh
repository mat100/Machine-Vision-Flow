#!/bin/bash
#
# Machine Vision Flow - Log Viewer
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Machine Vision Flow - Logs          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# Log selection
if [ "$1" == "backend" ] || [ "$1" == "python" ]; then
    LOG_FILE="$PROJECT_DIR/python-backend/backend.log"
    if [ -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}Showing Python backend log:${NC}"
        tail -f "$LOG_FILE"
    else
        echo "Backend log not found"
    fi
elif [ "$1" == "node-red" ] || [ "$1" == "nodered" ]; then
    LOG_FILE="$PROJECT_DIR/node-red.log"
    if [ -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}Showing Node-RED log:${NC}"
        tail -f "$LOG_FILE"
    else
        echo "Node-RED log not found"
    fi
elif [ "$1" == "clear" ]; then
    echo "Clearing log files..."
    > "$PROJECT_DIR/python-backend/backend.log" 2>/dev/null || true
    > "$PROJECT_DIR/node-red.log" 2>/dev/null || true
    echo "Log files cleared"
else
    # Show both logs
    echo -e "${YELLOW}Following all logs (Ctrl+C to exit)...${NC}"
    echo

    # Use multitail if available
    if command -v multitail &> /dev/null; then
        multitail -i "$PROJECT_DIR/python-backend/backend.log" \
                  -i "$PROJECT_DIR/node-red.log"
    else
        # Fallback to tail with marking
        tail -f "$PROJECT_DIR/python-backend/backend.log" \
                "$PROJECT_DIR/node-red.log" 2>/dev/null | \
        while IFS= read -r line; do
            if [[ $line == *"python-backend/backend.log"* ]]; then
                echo -e "${BLUE}[BACKEND]${NC} $line"
            elif [[ $line == *"node-red.log"* ]]; then
                echo -e "${YELLOW}[NODE-RED]${NC} $line"
            else
                echo "$line"
            fi
        done
    fi
fi