#!/bin/bash
#
# Machine Vision Flow - Python Backend Development Mode
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/services.sh"

# Parse arguments
USE_CONFIG_DEV=true
AUTO_RELOAD=true
WATCH_FILES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-reload)
            AUTO_RELOAD=false
            shift
            ;;
        --watch)
            WATCH_FILES=true
            shift
            ;;
        --config)
            USE_CONFIG_DEV=false
            shift
            ;;
        *)
            shift
            ;;
    esac
done

cleanup() {
    set +e
    echo
    log_warn "Stopping Python backend..."

    # Kill uvicorn process
    if [ -n "${UVICORN_PID:-}" ] && ps -p "$UVICORN_PID" >/dev/null 2>&1; then
        kill "$UVICORN_PID" 2>/dev/null || true
    fi

    # Clean up any orphaned Python processes
    pkill -f "uvicorn main:app" 2>/dev/null || true

    rm -f "$BACKEND_PID_FILE"
    log_info "Python backend stopped"
    exit 0
}
trap cleanup INT TERM

print_banner "Python Backend - Development Mode" "$BLUE"

# Ensure virtual environment and dependencies
ensure_python_backend_env false

# Check for config.dev.yaml
CONFIG_FILE="$BACKEND_DIR/config.yaml"
if [ "$USE_CONFIG_DEV" = true ] && [ -f "$BACKEND_DIR/config.dev.yaml" ]; then
    CONFIG_FILE="$BACKEND_DIR/config.dev.yaml"
    log_info "Using development configuration: config.dev.yaml"
else
    log_info "Using standard configuration: config.yaml"
fi

# Build uvicorn command
UVICORN_CMD="$BACKEND_VENV_DIR/bin/uvicorn main:app"
UVICORN_ARGS="--host 0.0.0.0 --port 8000"

# Add reload flags if enabled
if [ "$AUTO_RELOAD" = true ]; then
    UVICORN_ARGS="$UVICORN_ARGS --reload"
    UVICORN_ARGS="$UVICORN_ARGS --reload-dir api"
    UVICORN_ARGS="$UVICORN_ARGS --reload-dir core"
    UVICORN_ARGS="$UVICORN_ARGS --reload-dir vision"
    UVICORN_ARGS="$UVICORN_ARGS --reload-dir utils"
    UVICORN_ARGS="$UVICORN_ARGS --reload-exclude '*.log'"
    UVICORN_ARGS="$UVICORN_ARGS --reload-exclude '*.pyc'"
    UVICORN_ARGS="$UVICORN_ARGS --reload-exclude '__pycache__'"
    UVICORN_ARGS="$UVICORN_ARGS --reload-exclude 'venv'"
    log_success "Auto-reload enabled - changes will be detected automatically"
else
    log_warn "Auto-reload disabled - manual restart required for changes"
fi

# Add development-specific flags
UVICORN_ARGS="$UVICORN_ARGS --log-level debug"
UVICORN_ARGS="$UVICORN_ARGS --access-log"

# Export config file path for the app to use
export MV_CONFIG_FILE="$CONFIG_FILE"

echo
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Starting Python Backend in Development Mode${NC}"
echo
echo -e "Configuration:   ${YELLOW}$CONFIG_FILE${NC}"
echo -e "Auto-reload:     ${YELLOW}$([ "$AUTO_RELOAD" = true ] && echo "Enabled" || echo "Disabled")${NC}"
echo -e "Virtual env:     ${YELLOW}$BACKEND_VENV_DIR${NC}"
echo
echo -e "Service will be available at:"
echo -e "  • API:         ${GREEN}http://localhost:8000${NC}"
echo -e "  • Swagger UI:  ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  • ReDoc:       ${GREEN}http://localhost:8000/redoc${NC}"
echo
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo

# Change to backend directory
cd "$BACKEND_DIR"

# Start uvicorn
if [ "$AUTO_RELOAD" = true ]; then
    log_info "Starting with auto-reload..."
    log_info "Watching directories: api/, core/, vision/, utils/"
    echo
fi

# Run uvicorn (it will handle the output directly)
exec $UVICORN_CMD $UVICORN_ARGS