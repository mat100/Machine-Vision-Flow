#!/bin/bash
#
# Machine Vision Flow - Status Script
# Shows status of all services.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"

print_banner "Machine Vision Flow - Status" "$BLUE"

echo -e "${BLUE}Python Backend:${NC}"
if check_port 8000; then
    echo -e "  Status:  ${GREEN}● Running${NC}"
    echo -e "  URL:     http://localhost:8000"
    echo -e "  API:     http://localhost:8000/docs"
    if [ -f "$BACKEND_PID_FILE" ]; then
        echo -e "  PID:     $(cat "$BACKEND_PID_FILE")"
    fi
else
    echo -e "  Status:  ${RED}○ Stopped${NC}"
fi

echo
echo -e "${BLUE}Node-RED:${NC}"
if check_port 1880; then
    echo -e "  Status:  ${GREEN}● Running${NC}"
    echo -e "  URL:     http://localhost:1880"
    if [ -f "$NODE_RED_PID_FILE" ]; then
        echo -e "  PID:     $(cat "$NODE_RED_PID_FILE")"
    fi
else
    echo -e "  Status:  ${RED}○ Stopped${NC}"
fi

echo
echo -e "${BLUE}Log Files:${NC}"
if [ -f "$BACKEND_LOG_FILE" ]; then
    size=$(du -h "$BACKEND_LOG_FILE" | cut -f1)
    echo -e "  Backend: $BACKEND_LOG_FILE ($size)"
fi
if [ -f "$NODE_RED_LOG_FILE" ]; then
    size=$(du -h "$NODE_RED_LOG_FILE" | cut -f1)
    echo -e "  Node-RED: $NODE_RED_LOG_FILE ($size)"
fi

echo
echo -e "${BLUE}System Info:${NC}"
if command -v python3 >/dev/null 2>&1; then
    python_version=$(python3 --version 2>/dev/null | awk '{print $2}')
else
    python_version="missing"
fi
if command -v node >/dev/null 2>&1; then
    node_version=$(node --version 2>/dev/null)
else
    node_version="missing"
fi
if command -v npm >/dev/null 2>&1; then
    npm_version=$(npm --version 2>/dev/null)
else
    npm_version="missing"
fi

echo -e "  Python:  $python_version"
echo -e "  Node:    $node_version"
echo -e "  npm:     $npm_version"

echo
echo -e "${BLUE}Cameras:${NC}"
if check_port 8000; then
    if command -v curl >/dev/null 2>&1; then
        response=$(curl -s -X POST http://localhost:8000/api/camera/list 2>/dev/null || echo "[]")
        if [ "$response" != "[]" ] && [ -n "$response" ]; then
            if command -v python3 >/dev/null 2>&1; then
                echo "$response" | python3 - <<'PY' 2>/dev/null || echo -e "  ${YELLOW}Unable to parse camera list${NC}"
import json, sys
cameras = json.load(sys.stdin)
for cam in cameras:
    status = '✓' if cam.get('connected') else ' '
    print(f"  [{status}] {cam.get('id')}: {cam.get('name')} ({cam.get('type')})")
PY
            else
                echo -e "  ${YELLOW}Python not available to parse camera list${NC}"
            fi
        else
            echo -e "  ${YELLOW}No cameras detected${NC}"
        fi
    else
        echo -e "  ${YELLOW}curl command not available${NC}"
    fi
else
    echo -e "  ${YELLOW}Backend not running${NC}"
fi

echo
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "  ${GREEN}make start${NC}  - Start all services"
echo -e "  ${RED}make stop${NC}   - Stop all services"
echo -e "  ${YELLOW}make reload${NC} - Restart all services"
echo -e "  ${BLUE}make logs${NC}   - View logs"
echo -e "${BLUE}════════════════════════════════════════${NC}"
