#!/bin/bash
#
# Machine Vision Flow - Stop Script
# Stops Python backend and Node-RED
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${RED}╔════════════════════════════════════════╗${NC}"
echo -e "${RED}║     Machine Vision Flow - Shutdown     ║${NC}"
echo -e "${RED}╚════════════════════════════════════════╝${NC}"
echo

# Stop Python backend
if [ -f "$PROJECT_DIR/python-backend/backend.pid" ]; then
    PID=$(cat "$PROJECT_DIR/python-backend/backend.pid")
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "Stopping Python backend (PID: $PID)..."
        kill $PID
        sleep 2
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}Force stopping Python backend...${NC}"
            kill -9 $PID
        fi
        echo -e "${GREEN}✓ Python backend stopped${NC}"
    else
        echo -e "${YELLOW}Python backend not running (stale PID file)${NC}"
    fi
    rm -f "$PROJECT_DIR/python-backend/backend.pid"
else
    echo -e "${YELLOW}Python backend PID file not found${NC}"
    # Try to find process
    PIDS=$(pgrep -f "python3 main.py" || true)
    if [ ! -z "$PIDS" ]; then
        echo -e "Found Python backend process(es): $PIDS"
        kill $PIDS 2>/dev/null || true
        echo -e "${GREEN}✓ Python backend stopped${NC}"
    fi
fi

# Stop Node-RED
if [ -f "$PROJECT_DIR/node-red.pid" ]; then
    PID=$(cat "$PROJECT_DIR/node-red.pid")
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "Stopping Node-RED (PID: $PID)..."
        kill $PID
        sleep 2
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}Force stopping Node-RED...${NC}"
            kill -9 $PID
        fi
        echo -e "${GREEN}✓ Node-RED stopped${NC}"
    else
        echo -e "${YELLOW}Node-RED not running (stale PID file)${NC}"
    fi
    rm -f "$PROJECT_DIR/node-red.pid"
else
    echo -e "${YELLOW}Node-RED PID file not found${NC}"
    # Try to use node-red-stop
    if command -v node-red-stop &> /dev/null; then
        echo -e "Using node-red-stop command..."
        node-red-stop
        echo -e "${GREEN}✓ Node-RED stopped${NC}"
    fi
fi

echo
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}All services stopped${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"