#!/bin/bash
#
# Machine Vision Flow - VSCode Port Forwarding Setup
# Automatically forwards ports when running in VSCode
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"

is_vscode() {
    if [ -n "${VSCODE_PID:-}" ] || [ -n "${VSCODE_IPC_HOOK:-}" ] || [ -n "${VSCODE_GIT_IPC_HANDLE:-}" ] || [ "${TERM_PROGRAM:-}" = "vscode" ]; then
        return 0
    fi
    if [ -n "${SSH_CLIENT:-}" ] && [ -n "${VSCODE_INJECTION:-}" ]; then
        return 0
    fi
    return 1
}

forward_port() {
    local port="$1"
    local name="$2"

    if check_port "$port"; then
        echo -e "${GREEN}✓${NC} Port $port ($name) is accessible"
    else
        echo -e "${YELLOW}⚠${NC} Port $port ($name) may need manual forwarding"
    fi
}

print_banner "VSCode Port Forwarding Setup" "$BLUE"
echo

if is_vscode; then
    echo -e "${GREEN}✓ Running in VSCode environment${NC}"
    echo
    echo -e "${YELLOW}VSCode Auto Port Forwarding:${NC}"
    echo "VSCode will automatically forward these ports when services start:"
    echo
    echo -e "  • Port ${GREEN}8000${NC} - Python Backend API"
    echo -e "  • Port ${GREEN}1880${NC} - Node-RED Interface"
    echo

    sleep 2

    echo "Checking port status..."
    forward_port 8000 "Python Backend"
    forward_port 1880 "Node-RED"

    echo
    echo -e "${GREEN}Port forwarding setup complete!${NC}"
    echo
    echo "Access your services at:"
    echo -e "  • Python Backend: ${GREEN}http://localhost:8000${NC}"
    echo -e "  • API Docs:       ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  • Node-RED:       ${GREEN}http://localhost:1880${NC}"
    echo

    if [ -n "${SSH_CLIENT:-}" ]; then
        echo -e "${BLUE}Note: You're connected via SSH${NC}"
        echo "VSCode should automatically forward these ports to your local machine."
        echo "If not, you can manually forward them in VSCode:"
        echo "  1. Open Command Palette (Ctrl+Shift+P / Cmd+Shift+P)"
        echo "  2. Type: 'Forward a Port'"
        echo "  3. Enter the port number (8000 or 1880)"
    fi

    if command -v code >/dev/null 2>&1; then
        echo
        echo -e "${BLUE}Opening VSCode Ports panel...${NC}"
        code --goto "workbench.panel.ports" 2>/dev/null || true
    fi
else
    echo -e "${YELLOW}⚠ Not running in VSCode environment${NC}"
    echo "Port forwarding setup is only needed when running in VSCode."
    echo
    echo "Services are available at:"
    echo -e "  • Python Backend: ${GREEN}http://localhost:8000${NC}"
    echo -e "  • API Docs:       ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  • Node-RED:       ${GREEN}http://localhost:1880${NC}"
fi

echo -e "${BLUE}════════════════════════════════════════${NC}"
