#!/bin/bash
#
# Machine Vision Flow - Enhanced Development Mode with Auto-Reload
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/services.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/watchers.sh"

# Parse command line arguments
AUTO_RELOAD=true
WATCH_MODE="all"  # all, python, nodered, none
USE_TMUX=false
USE_SPLIT=false
COLOR_LOGS=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-reload)
            AUTO_RELOAD=false
            shift
            ;;
        --watch)
            WATCH_MODE="$2"
            shift 2
            ;;
        --tmux)
            USE_TMUX=true
            shift
            ;;
        --split)
            USE_SPLIT=true
            shift
            ;;
        --no-color)
            COLOR_LOGS=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --no-reload      Disable auto-reload"
            echo "  --watch MODE     Set watch mode (all|python|nodered|none)"
            echo "  --tmux           Use tmux for split-screen logs"
            echo "  --split          Split terminal for logs (requires tmux)"
            echo "  --no-color       Disable colored logs"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Track what we started
STARTED_PYTHON=false
STARTED_NODERED=false
PYTHON_PID=""
NODERED_PID=""
WATCHER_PIDS=""
TAIL_PID=""

cleanup() {
    set +e
    echo
    log_warn "Shutting down development mode..."

    # Stop watchers first
    if [ -n "$WATCHER_PIDS" ]; then
        log_info "Stopping file watchers..."
        stop_watchers "$WATCHER_PIDS"
    fi

    # Stop tail process
    if [ -n "$TAIL_PID" ] && ps -p "$TAIL_PID" >/dev/null 2>&1; then
        kill "$TAIL_PID" 2>/dev/null || true
    fi

    # Stop Python backend
    if [ "$STARTED_PYTHON" = true ]; then
        log_info "Stopping Python backend..."
        if [ -n "$PYTHON_PID" ]; then
            kill "$PYTHON_PID" 2>/dev/null || true
        fi
        stop_python_backend
    fi

    # Stop Node-RED
    if [ "$STARTED_NODERED" = true ]; then
        log_info "Stopping Node-RED..."
        if [ -n "$NODERED_PID" ]; then
            kill "$NODERED_PID" 2>/dev/null || true
        fi
        stop_node_red
    fi

    # Kill tmux session if we created one
    if [ "$USE_TMUX" = true ]; then
        tmux kill-session -t mvflow-dev 2>/dev/null || true
    fi

    log_success "Development mode stopped"
    exit 0
}
trap cleanup INT TERM

print_banner "Machine Vision Flow - Enhanced Development Mode" "$GREEN"

# Check for required tools
check_dev_requirements() {
    local missing_tools=()

    if [ "$AUTO_RELOAD" = true ] && [ "$WATCH_MODE" != "none" ]; then
        if ! command -v inotifywait >/dev/null 2>&1; then
            missing_tools+=("inotify-tools")
        fi
    fi

    if [ "$USE_TMUX" = true ] || [ "$USE_SPLIT" = true ]; then
        if ! command -v tmux >/dev/null 2>&1; then
            missing_tools+=("tmux")
        fi
    fi

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_warn "Missing development tools: ${missing_tools[*]}"
        log_info "Install with: sudo apt-get install ${missing_tools[*]}"
        echo
    fi
}

# Start Python backend with auto-reload
start_python_dev() {
    log_info "Starting Python backend with auto-reload..."

    # Ensure virtual environment
    ensure_python_backend_env false

    # Check for dev config
    local config_arg=""
    if [ -f "$BACKEND_DIR/config.dev.yaml" ]; then
        export MV_CONFIG_FILE="$BACKEND_DIR/config.dev.yaml"
        log_info "Using development configuration"
    fi

    # Start with uvicorn in reload mode
    pushd "$BACKEND_DIR" >/dev/null
    nohup "$BACKEND_VENV_DIR/bin/uvicorn" main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --reload-dir api \
        --reload-dir core \
        --reload-dir vision \
        --reload-dir utils \
        --log-level debug \
        > "$BACKEND_LOG_FILE" 2>&1 &
    PYTHON_PID=$!
    popd >/dev/null

    echo "$PYTHON_PID" > "$BACKEND_PID_FILE"
    STARTED_PYTHON=true

    wait_for_port 8000 "Python backend" 10
    log_success "Python backend started with auto-reload (PID: $PYTHON_PID)"
}

# Start Node-RED with file watching
start_nodered_dev() {
    log_info "Starting Node-RED..."

    ensure_node_red_dependencies false

    pushd "$NODE_RED_USER_DIR" >/dev/null
    nohup node-red > "$NODE_RED_LOG_FILE" 2>&1 &
    NODERED_PID=$!
    popd >/dev/null

    echo "$NODERED_PID" > "$NODE_RED_PID_FILE"
    STARTED_NODERED=true

    wait_for_port 1880 "Node-RED" 15
    log_success "Node-RED started (PID: $NODERED_PID)"
}

# Restart Node-RED when changes detected
restart_nodered_callback() {
    log_info "Node-RED files changed, restarting..."

    # Stop current instance
    if [ -n "$NODERED_PID" ] && ps -p "$NODERED_PID" >/dev/null 2>&1; then
        kill "$NODERED_PID" 2>/dev/null || true
        sleep 2
    fi

    # Clear module cache and reinstall
    pushd "$NODE_RED_USER_DIR" >/dev/null
    rm -rf node_modules/.cache 2>/dev/null || true
    npm install "$PROJECT_ROOT/node-red" --force >/dev/null 2>&1
    popd >/dev/null

    # Restart Node-RED
    start_nodered_dev
    log_success "Node-RED restarted with updated nodes"
}

# Start file watchers based on mode
start_file_watchers() {
    local pids=""

    case "$WATCH_MODE" in
        all)
            log_info "Starting watchers for all services..."
            # Python backend already has uvicorn reload
            # Just watch Node-RED nodes
            watch_files "$PROJECT_ROOT/node-red/nodes" "js,html,json" restart_nodered_callback 2 &
            pids="$! $pids"
            ;;
        python)
            log_info "Python backend has built-in auto-reload via uvicorn"
            ;;
        nodered)
            log_info "Starting Node-RED file watcher..."
            watch_files "$PROJECT_ROOT/node-red/nodes" "js,html,json" restart_nodered_callback 2 &
            pids="$! $pids"
            ;;
        none)
            log_info "File watching disabled"
            ;;
    esac

    WATCHER_PIDS="$pids"
}

# Color-coded log output
tail_logs_with_color() {
    if [ "$COLOR_LOGS" = true ]; then
        # Use awk to color-code log lines
        tail -f "$BACKEND_LOG_FILE" "$NODE_RED_LOG_FILE" | awk '
            /ERROR/ {print "\033[31m" $0 "\033[0m"; next}
            /WARN/ {print "\033[33m" $0 "\033[0m"; next}
            /INFO/ {print "\033[36m" $0 "\033[0m"; next}
            /DEBUG/ {print "\033[90m" $0 "\033[0m"; next}
            /backend\.log/ {print "\033[34m[PYTHON] \033[0m" $0; next}
            /node-red\.log/ {print "\033[35m[NODE-RED] \033[0m" $0; next}
            {print $0}
        ' &
    else
        tail -f "$BACKEND_LOG_FILE" "$NODE_RED_LOG_FILE" &
    fi
    TAIL_PID=$!
}

# Start with tmux split screen
start_with_tmux() {
    log_info "Starting services in tmux session..."

    # Kill existing session if it exists
    tmux kill-session -t mvflow-dev 2>/dev/null || true

    # Create new tmux session
    tmux new-session -d -s mvflow-dev -n "MV Flow Dev"

    # Split horizontally for Python backend
    tmux send-keys -t mvflow-dev:0 "cd $BACKEND_DIR && $BACKEND_VENV_DIR/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000" C-m

    # Split vertically for Node-RED
    tmux split-window -v -t mvflow-dev:0
    tmux send-keys -t mvflow-dev:0.1 "cd $NODE_RED_USER_DIR && node-red" C-m

    # Split for logs
    tmux split-window -h -t mvflow-dev:0.0
    tmux send-keys -t mvflow-dev:0.2 "tail -f $BACKEND_LOG_FILE $NODE_RED_LOG_FILE" C-m

    # Attach to session
    tmux attach-session -t mvflow-dev
}

# Main execution
check_dev_requirements

# Check if services are already running
ALREADY_RUNNING=false
if check_port 8000 || check_port 1880; then
    log_warn "Some services are already running"
    read -p "Stop existing services and restart? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "$SCRIPT_DIR/stop.sh"
        sleep 2
    else
        log_info "Exiting. Stop services manually with: make stop"
        exit 1
    fi
fi

# Start with tmux if requested
if [ "$USE_TMUX" = true ] || [ "$USE_SPLIT" = true ]; then
    start_with_tmux
    exit 0
fi

# Start services
log_info "Starting services in development mode..."
start_python_dev
start_nodered_dev

# Setup VS Code ports if available
if [ -f "$SCRIPT_DIR/setup_vscode_ports.sh" ]; then
    "$SCRIPT_DIR/setup_vscode_ports.sh"
fi

# Start file watchers if enabled
if [ "$AUTO_RELOAD" = true ] && [ "$WATCH_MODE" != "none" ]; then
    if check_inotify; then
        start_file_watchers
    else
        log_warn "File watching disabled - inotify-tools not installed"
    fi
fi

# Display status
echo
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Enhanced Development Mode Active!${NC}"
echo
echo -e "Services:"
echo -e "  • Python Backend:  ${GREEN}http://localhost:8000${NC}"
echo -e "  • Swagger UI:      ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  • ReDoc:           ${GREEN}http://localhost:8000/redoc${NC}"
echo -e "  • Node-RED:        ${GREEN}http://localhost:1880${NC}"
echo
echo -e "Features:"
echo -e "  • Auto-reload:     ${YELLOW}$([ "$AUTO_RELOAD" = true ] && echo "Enabled" || echo "Disabled")${NC}"
echo -e "  • Watch mode:      ${YELLOW}$WATCH_MODE${NC}"
echo -e "  • Color logs:      ${YELLOW}$([ "$COLOR_LOGS" = true ] && echo "Yes" || echo "No")${NC}"
echo
if [ "$AUTO_RELOAD" = true ]; then
    echo -e "${CYAN}File changes will trigger automatic reload:${NC}"
    echo -e "  • Python: *.py files auto-reload via uvicorn"
    echo -e "  • Node-RED: *.js/*.html files trigger restart"
fi
echo
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo

# Start tailing logs
log_info "Following service logs..."
echo
touch "$BACKEND_LOG_FILE" "$NODE_RED_LOG_FILE"
tail_logs_with_color

# Wait for tail process
wait "$TAIL_PID"
