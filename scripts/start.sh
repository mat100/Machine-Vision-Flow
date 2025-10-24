#!/bin/bash
#
# Machine Vision Flow - Start Script
# Starts the Python backend and Node-RED services.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/services.sh"

BACKEND_STARTED=false
NODERED_STARTED=false
BACKEND_PID=""
NODERED_PID=""
FOLLOW_LOGS=false
FORCE_DEPS=false

usage() {
    cat <<'EOF'
Usage: start.sh [options]

Options:
  --follow, -f     Follow service logs after startup
  --force-deps     Reinstall runtime dependencies before starting
  --help           Show this help and exit
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --follow|-f)
            FOLLOW_LOGS=true
            ;;
        --force-deps)
            FORCE_DEPS=true
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            log_warn "Ignoring unknown option: $1"
            ;;
    esac
    shift
done

cleanup() {
    set +e
    echo
    log_warn "Caught interrupt signal, shutting down services..."

    if [ "$FOLLOW_LOGS" = true ] && [ -n "${TAIL_PID:-}" ]; then
        kill "$TAIL_PID" 2>/dev/null || true
    fi

    if [ "$NODERED_STARTED" = true ]; then
        log_info "Stopping Node-RED..."
        stop_node_red "$NODERED_PID"
        log_success "Node-RED stopped"
    fi

    if [ "$BACKEND_STARTED" = true ]; then
        log_info "Stopping Python backend..."
        stop_python_backend "$BACKEND_PID"
        log_success "Python backend stopped"
    fi

    exit 0
}
trap cleanup INT TERM

print_banner "Machine Vision Flow - Startup" "$GREEN"

require_command python3 "Install Python 3 to run the backend."
require_command npm "Install Node.js and npm to manage Node-RED nodes."
require_command node-red "Install Node-RED with: npm install -g node-red"

echo

if check_port 8000; then
    log_warn "⚠ Python backend already running on port 8000"
else
    log_info "Starting Python backend..."
    start_python_backend "$FORCE_DEPS"
    BACKEND_PID="$(cat "$BACKEND_PID_FILE")"
    BACKEND_STARTED=true
    log_success "✓ Python backend PID: $BACKEND_PID"
    wait_for_port 8000 "Python backend"
fi

echo

if check_port 1880; then
    log_warn "⚠ Node-RED already running on port 1880"
else
    log_info "Starting Node-RED..."
    start_node_red "$FORCE_DEPS"
    NODERED_PID="$(cat "$NODE_RED_PID_FILE")"
    NODERED_STARTED=true
    log_success "✓ Node-RED PID: $NODERED_PID"
    wait_for_port 1880 "Node-RED"
fi

echo
print_banner "System is ready!" "$GREEN"
echo -e "Python Backend: ${GREEN}http://localhost:8000${NC}"
echo -e "API Docs:       ${GREEN}http://localhost:8000/docs${NC}"
echo -e "Node-RED:       ${GREEN}http://localhost:1880${NC}"
echo
echo -e "${YELLOW}To stop the services, run:${NC} ./stop.sh"

if [ "$FOLLOW_LOGS" = true ]; then
    echo
    log_info "Following logs (Ctrl+C to exit)..."
    touch "$BACKEND_LOG_FILE" "$NODE_RED_LOG_FILE"
    tail -f "$BACKEND_LOG_FILE" "$NODE_RED_LOG_FILE" &
    TAIL_PID=$!
    wait "$TAIL_PID"
fi
