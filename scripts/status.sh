#!/bin/bash
#
# Machine Vision Flow - Status Script
# Shows status of all services
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Machine Vision Flow - Status        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# Function to check port
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Python Backend
echo -e "${BLUE}Python Backend:${NC}"
if check_port 8000; then
    echo -e "  Status:  ${GREEN}● Running${NC}"
    echo -e "  URL:     http://localhost:8000"
    echo -e "  API:     http://localhost:8000/docs"
    if [ -f "$PROJECT_DIR/python-backend/backend.pid" ]; then
        PID=$(cat "$PROJECT_DIR/python-backend/backend.pid")
        echo -e "  PID:     $PID"
    fi
else
    echo -e "  Status:  ${RED}○ Stopped${NC}"
fi

echo

# Node-RED
echo -e "${BLUE}Node-RED:${NC}"
if check_port 1880; then
    echo -e "  Status:  ${GREEN}● Running${NC}"
    echo -e "  URL:     http://localhost:1880"
    if [ -f "$PROJECT_DIR/node-red.pid" ]; then
        PID=$(cat "$PROJECT_DIR/node-red.pid")
        echo -e "  PID:     $PID"
    fi
else
    echo -e "  Status:  ${RED}○ Stopped${NC}"
fi

echo

# Check logs
echo -e "${BLUE}Log Files:${NC}"
if [ -f "$PROJECT_DIR/python-backend/backend.log" ]; then
    SIZE=$(du -h "$PROJECT_DIR/python-backend/backend.log" | cut -f1)
    echo -e "  Backend: $PROJECT_DIR/python-backend/backend.log ($SIZE)"
fi
if [ -f "$PROJECT_DIR/node-red.log" ]; then
    SIZE=$(du -h "$PROJECT_DIR/node-red.log" | cut -f1)
    echo -e "  Node-RED: $PROJECT_DIR/node-red.log ($SIZE)"
fi

echo

# System info
echo -e "${BLUE}System Info:${NC}"
echo -e "  Python:  $(python3 --version 2>&1 | cut -d' ' -f2)"
echo -e "  Node:    $(node --version)"
echo -e "  npm:     $(npm --version)"

# Check cameras
echo
echo -e "${BLUE}Cameras:${NC}"
if check_port 8000; then
    # Attempt to load camera list
    CAMERAS=$(curl -s -X POST http://localhost:8000/api/camera/list 2>/dev/null || echo "[]")
    if [ "$CAMERAS" != "[]" ]; then
        echo "$CAMERAS" | python3 -c "
import sys, json
cameras = json.load(sys.stdin)
for cam in cameras:
    status = '✓' if cam.get('connected') else ' '
    print(f\"  [{status}] {cam['id']}: {cam['name']} ({cam['type']})\")
" 2>/dev/null || echo -e "  ${YELLOW}Unable to parse camera list${NC}"
    else
        echo -e "  ${YELLOW}No cameras detected${NC}"
    fi
else
    echo -e "  ${YELLOW}Backend not running${NC}"
fi

echo
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "Commands:"
echo -e "  ${GREEN}./start.sh${NC}   - Start all services"
echo -e "  ${RED}./stop.sh${NC}    - Stop all services"
echo -e "  ${YELLOW}./restart.sh${NC} - Restart all services"
echo -e "  ${BLUE}./logs.sh${NC}    - View logs"
echo -e "${BLUE}════════════════════════════════════════${NC}"