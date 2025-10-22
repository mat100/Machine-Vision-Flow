#!/bin/bash
#
# Setup Development Tools for Machine Vision Flow
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"

print_banner "Development Tools Setup" "$CYAN"

# Check for required development tools
echo "Checking for required development tools..."
echo

MISSING_TOOLS=()
OPTIONAL_TOOLS=()

# Required tools
if ! command -v inotifywait >/dev/null 2>&1; then
    MISSING_TOOLS+=("inotify-tools")
    echo "❌ inotify-tools - Required for file watching"
else
    echo "✓ inotify-tools installed"
fi

# Optional but recommended tools
if ! command -v tmux >/dev/null 2>&1; then
    OPTIONAL_TOOLS+=("tmux")
    echo "⚠ tmux - Optional, for split-screen development"
else
    echo "✓ tmux installed"
fi

if ! command -v entr >/dev/null 2>&1; then
    OPTIONAL_TOOLS+=("entr")
    echo "⚠ entr - Optional, alternative file watcher"
else
    echo "✓ entr installed"
fi

if ! command -v htop >/dev/null 2>&1; then
    OPTIONAL_TOOLS+=("htop")
    echo "⚠ htop - Optional, for process monitoring"
else
    echo "✓ htop installed"
fi

echo

# Install missing required tools
if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Missing required tools:${NC} ${MISSING_TOOLS[*]}"
    echo
    read -p "Install required tools now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installing required tools..."
        sudo apt-get update
        sudo apt-get install -y "${MISSING_TOOLS[@]}"
        log_success "Required tools installed!"
    else
        log_warn "Skipping installation. Development mode may not work properly."
    fi
    echo
fi

# Ask about optional tools
if [ ${#OPTIONAL_TOOLS[@]} -gt 0 ]; then
    echo -e "${CYAN}Optional tools not installed:${NC} ${OPTIONAL_TOOLS[*]}"
    echo
    read -p "Install optional tools for better development experience? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installing optional tools..."
        sudo apt-get install -y "${OPTIONAL_TOOLS[@]}"
        log_success "Optional tools installed!"
    fi
    echo
fi

# Check Python development packages
echo "Checking Python development setup..."
if [ -f "$BACKEND_DIR/requirements.txt" ]; then
    if [ ! -d "$BACKEND_VENV_DIR" ]; then
        log_warn "Python virtual environment not found"
        read -p "Create Python virtual environment now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 -m venv "$BACKEND_VENV_DIR"
            "$BACKEND_VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
            log_success "Python environment created and dependencies installed"
        fi
    else
        log_success "Python virtual environment exists"
    fi
fi
echo

# Check Node-RED setup
echo "Checking Node-RED setup..."
if command -v node-red >/dev/null 2>&1; then
    log_success "Node-RED is installed"

    if [ -d "$NODE_RED_USER_DIR" ]; then
        if [ ! -L "$NODE_RED_USER_DIR/node_modules/node-red-contrib-machine-vision-flow" ]; then
            log_warn "Machine Vision Flow nodes not linked"
            read -p "Install Machine Vision Flow nodes? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                pushd "$NODE_RED_USER_DIR" >/dev/null
                npm install "$PROJECT_ROOT/node-red"
                npm install node-red-contrib-image-output
                popd >/dev/null
                log_success "Node-RED nodes installed"
            fi
        else
            log_success "Machine Vision Flow nodes are linked"
        fi
    fi
else
    log_warn "Node-RED not installed"
    echo "Install with: npm install -g node-red"
fi
echo

# Summary
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Development Tools Setup Complete!${NC}"
echo
echo "You can now use the enhanced development mode:"
echo
echo -e "  ${CYAN}make dev${NC}           - Full development mode with auto-reload"
echo -e "  ${CYAN}make dev-python${NC}    - Python backend only with hot-reload"
echo -e "  ${CYAN}make dev-nodered${NC}   - Node-RED only with file watching"
echo -e "  ${CYAN}make dev-tmux${NC}      - Split-screen mode with tmux"
echo
echo "Tips:"
echo "  • Python files auto-reload when changed (*.py)"
echo "  • Node-RED nodes restart when changed (*.js, *.html)"
echo "  • Use config.dev.yaml for development-specific settings"
echo "  • Logs are color-coded for easier debugging"
echo
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"