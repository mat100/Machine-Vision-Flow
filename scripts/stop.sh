#!/bin/bash
#
# Machine Vision Flow - Stop Script
# Stops Python backend and Node-RED services.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/services.sh"

print_banner "Machine Vision Flow - Shutdown" "$RED"

BACKEND_STOPPED=false
NODERED_STOPPED=false

if [ -f "$BACKEND_PID_FILE" ] || check_port 8000; then
    log_info "Stopping Python backend..."
    stop_python_backend
    BACKEND_STOPPED=true
    log_success "✓ Python backend stopped"
else
    log_warn "Python backend not running"
fi

echo

if [ -f "$NODE_RED_PID_FILE" ] || check_port 1880; then
    log_info "Stopping Node-RED..."
    stop_node_red
    NODERED_STOPPED=true
    log_success "✓ Node-RED stopped"
else
    log_warn "Node-RED not running"
fi

echo
print_banner "All services stopped" "$GREEN"
