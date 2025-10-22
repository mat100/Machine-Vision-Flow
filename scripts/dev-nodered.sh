#!/bin/bash
#
# Machine Vision Flow - Node-RED Development Mode
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/services.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/watchers.sh"

# Parse arguments
WATCH_FILES=true
SAFE_MODE=false
DEBUG_MODE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-watch)
            WATCH_FILES=false
            shift
            ;;
        --safe)
            SAFE_MODE=true
            shift
            ;;
        --no-debug)
            DEBUG_MODE=false
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Track PIDs for cleanup
NODERED_PID=""
WATCHER_PID=""
RESTART_COUNT=0

cleanup() {
    set +e
    echo
    log_warn "Stopping Node-RED development mode..."

    # Stop file watcher
    if [ -n "$WATCHER_PID" ] && ps -p "$WATCHER_PID" >/dev/null 2>&1; then
        log_info "Stopping file watcher..."
        kill "$WATCHER_PID" 2>/dev/null || true
    fi

    # Stop Node-RED
    if [ -n "$NODERED_PID" ] && ps -p "$NODERED_PID" >/dev/null 2>&1; then
        log_info "Stopping Node-RED..."
        kill "$NODERED_PID" 2>/dev/null || true
    fi

    # Clean up any orphaned Node-RED processes
    pkill -f "node.*node-red" 2>/dev/null || true

    rm -f "$NODE_RED_PID_FILE"
    log_info "Node-RED stopped"
    exit 0
}
trap cleanup INT TERM

print_banner "Node-RED - Development Mode" "$MAGENTA"

# Ensure Node-RED dependencies are installed
ensure_node_red_dependencies false

# Function to restart Node-RED when changes detected
restart_nodered_on_change() {
    RESTART_COUNT=$((RESTART_COUNT + 1))

    log_info "Changes detected! Restart #$RESTART_COUNT"

    # Stop current Node-RED instance
    if [ -n "$NODERED_PID" ] && ps -p "$NODERED_PID" >/dev/null 2>&1; then
        log_info "Stopping current Node-RED instance..."
        kill "$NODERED_PID" 2>/dev/null || true
        sleep 2
    fi

    # Clear npm cache for our custom nodes (force reload)
    if [ -d "$NODE_RED_USER_DIR/node_modules/node-red-contrib-machine-vision-flow" ]; then
        log_info "Clearing Node-RED module cache..."
        rm -rf "$NODE_RED_USER_DIR/node_modules/.cache" 2>/dev/null || true
    fi

    # Reinstall the local package to pick up changes
    log_info "Reloading Machine Vision Flow nodes..."
    pushd "$NODE_RED_USER_DIR" >/dev/null
    npm install "$PROJECT_ROOT/node-red" --force >/dev/null 2>&1
    popd >/dev/null

    # Start Node-RED
    start_nodered_dev
}

# Function to start Node-RED in development mode
start_nodered_dev() {
    log_info "Starting Node-RED..."

    # Build Node-RED command with options
    NODERED_CMD="node-red"
    NODERED_ARGS=""

    if [ "$SAFE_MODE" = true ]; then
        NODERED_ARGS="$NODERED_ARGS --safe"
        log_warn "Starting in SAFE mode - flows not started automatically"
    fi

    if [ "$DEBUG_MODE" = true ]; then
        export NODE_ENV=development
        export DEBUG=*  # Enable all debug output
        log_info "Debug mode enabled"
    fi

    # Start Node-RED in background
    pushd "$NODE_RED_USER_DIR" >/dev/null
    nohup $NODERED_CMD $NODERED_ARGS >> "$NODE_RED_LOG_FILE" 2>&1 &
    NODERED_PID=$!
    popd >/dev/null

    echo "$NODERED_PID" > "$NODE_RED_PID_FILE"

    # Wait for Node-RED to be ready
    wait_for_port "$PORT_NODERED" "Node-RED" 15

    log_success "Node-RED started (PID: $NODERED_PID)"
}

# Function to watch for file changes
start_file_watcher() {
    log_info "Starting file watcher for Node-RED nodes..."

    # Directories to watch
    WATCH_DIRS="$PROJECT_ROOT/node-red/nodes"
    if [ -d "$PROJECT_ROOT/node-red/lib" ]; then
        WATCH_DIRS="$WATCH_DIRS $PROJECT_ROOT/node-red/lib"
    fi

    # Watch for changes in Node-RED custom nodes
    while true; do
        # Use inotifywait to detect changes
        inotifywait -r -e modify,create,delete,move \
            --include '.*\.\(js\|html\|json\)$' \
            $WATCH_DIRS 2>/dev/null

        # Debounce - wait a bit for multiple saves
        sleep 2

        # Restart Node-RED
        restart_nodered_on_change
    done &

    WATCHER_PID=$!
    log_success "File watcher started (PID: $WATCHER_PID)"
}

# Show development information
show_dev_info() {
    echo
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Node-RED Development Mode Active${NC}"
    echo
    echo -e "Configuration:"
    echo -e "  • User Directory:  ${YELLOW}$NODE_RED_USER_DIR${NC}"
    echo -e "  • Custom Nodes:    ${YELLOW}$PROJECT_ROOT/node-red/nodes${NC}"
    echo -e "  • File Watching:   ${YELLOW}$([ "$WATCH_FILES" = true ] && echo "Enabled" || echo "Disabled")${NC}"
    echo -e "  • Safe Mode:       ${YELLOW}$([ "$SAFE_MODE" = true ] && echo "Yes" || echo "No")${NC}"
    echo -e "  • Debug Mode:      ${YELLOW}$([ "$DEBUG_MODE" = true ] && echo "Enabled" || echo "Disabled")${NC}"
    echo
    echo -e "Service available at:"
    echo -e "  • Node-RED UI:     ${GREEN}http://localhost:1880${NC}"
    echo -e "  • Flow Editor:     ${GREEN}http://localhost:1880/admin${NC}"
    echo
    if [ "$WATCH_FILES" = true ]; then
        echo -e "${YELLOW}File changes will trigger automatic restart${NC}"
    fi
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo
}

# Main execution
log_info "Preparing Node-RED development environment..."

# Start Node-RED
start_nodered_dev

# Start file watcher if enabled
if [ "$WATCH_FILES" = true ]; then
    if check_inotify; then
        start_file_watcher
    else
        log_warn "File watching disabled - inotify-tools not installed"
        log_warn "Install with: sudo apt-get install inotify-tools"
    fi
fi

# Show information
show_dev_info

# Tail the log file
log_info "Following Node-RED logs..."
tail -f "$NODE_RED_LOG_FILE"