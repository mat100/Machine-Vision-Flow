#!/bin/bash
#
# Machine Vision Flow - Start Script
# Runs Python backend and Node-RED
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Machine Vision Flow - Startup      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
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

# Function to wait for port
wait_for_port() {
    local port=$1
    local service=$2
    local max_wait=30
    local waited=0

    echo -n "Waiting for $service to start on port $port..."
    while ! check_port $port && [ $waited -lt $max_wait ]; do
        echo -n "."
        sleep 1
        waited=$((waited + 1))
    done

    if [ $waited -eq $max_wait ]; then
        echo -e " ${RED}TIMEOUT${NC}"
        return 1
    else
        echo -e " ${GREEN}OK${NC}"
        return 0
    fi
}

# Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 found${NC}"

# Check Node-RED
echo "Checking Node-RED..."
if ! command -v node-red &> /dev/null; then
    echo -e "${YELLOW}⚠ Node-RED not found${NC}"
    echo "Install with: npm install -g node-red"
    exit 1
fi
echo -e "${GREEN}✓ Node-RED found${NC}"

echo

# Check if already running
if check_port 8000; then
    echo -e "${YELLOW}⚠ Python backend already running on port 8000${NC}"
else
    echo -e "${GREEN}Starting Python Backend...${NC}"
    cd "$PROJECT_DIR/python-backend"

    # Install dependencies if missing
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    if [ ! -f ".deps_installed" ]; then
        echo "Installing Python dependencies..."
        pip install -q -r requirements.txt
        touch .deps_installed
    fi

    # Run backend in background
    nohup python3 main.py > backend.log 2>&1 &
    BACKEND_PID=$!
    echo "Python backend PID: $BACKEND_PID"

    # Save PID for stop script
    echo $BACKEND_PID > backend.pid

    # Wait for startup
    wait_for_port 8000 "Python backend"
fi

echo

if check_port 1880; then
    echo -e "${YELLOW}⚠ Node-RED already running on port 1880${NC}"
else
    echo -e "${GREEN}Starting Node-RED...${NC}"

    # Check if MV nodes are installed
    cd "$HOME/.node-red"
    if [ ! -L "node_modules/node-red-contrib-machine-vision-flow" ] && [ ! -d "node_modules/node-red-contrib-machine-vision-flow" ]; then
        echo "Installing Machine Vision nodes..."
        npm install "$PROJECT_DIR/node-red"
    fi

    # Check image-output node
    if [ ! -d "node_modules/node-red-contrib-image-output" ]; then
        echo "Installing image-output node..."
        npm install node-red-contrib-image-output
    fi

    # Run Node-RED in background
    nohup node-red > "$PROJECT_DIR/node-red.log" 2>&1 &
    NODERED_PID=$!
    echo "Node-RED PID: $NODERED_PID"

    # Save PID
    echo $NODERED_PID > "$PROJECT_DIR/node-red.pid"

    # Wait for startup
    wait_for_port 1880 "Node-RED"
fi

echo
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}System is ready!${NC}"
echo
echo -e "Python Backend: ${GREEN}http://localhost:8000${NC}"
echo -e "API Docs:       ${GREEN}http://localhost:8000/docs${NC}"
echo -e "Node-RED:       ${GREEN}http://localhost:1880${NC}"
echo
echo -e "${YELLOW}To stop the services, run:${NC} ./stop.sh"
echo -e "${GREEN}════════════════════════════════════════${NC}"

# Follow logs (optional)
if [ "$1" == "--follow" ] || [ "$1" == "-f" ]; then
    echo
    echo "Following logs (Ctrl+C to exit)..."
    tail -f "$PROJECT_DIR/python-backend/backend.log" "$PROJECT_DIR/node-red.log"
fi