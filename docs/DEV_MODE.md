# Enhanced Development Mode Guide

## Quick Start

1. **Install required tools (one-time setup):**
   ```bash
   sudo apt-get install inotify-tools
   # or run: ./scripts/setup-dev-tools.sh
   ```

2. **Start development mode:**
   ```bash
   make dev
   ```

## Available Commands

### Basic Development Modes
- `make dev` - Full development mode with auto-reload for both services
- `make dev-python` - Python backend only with hot-reload
- `make dev-nodered` - Node-RED only with file watching
- `make dev-tmux` - Split-screen mode using tmux
- `make dev-logs` - Show colored, filtered logs

### Options for `make dev`
```bash
make dev                    # Default: auto-reload enabled
make dev ARGS="--no-reload" # Disable auto-reload
make dev ARGS="--watch python" # Watch only Python files
make dev ARGS="--watch nodered" # Watch only Node-RED files
make dev ARGS="--no-color" # Disable colored logs
make dev ARGS="--tmux"     # Use tmux split-screen
```

## How It Works

### Python Backend Auto-Reload
- **Monitored files:** `*.py`, `*.yaml`, `*.json` in `python-backend/`
- **Reload method:** uvicorn's built-in `--reload` flag
- **Reload time:** ~1-2 seconds
- **Config:** Uses `config.dev.yaml` if available

### Node-RED Auto-Restart
- **Monitored files:** `*.js`, `*.html`, `*.json` in `node-red/nodes/`
- **Reload method:** Full Node-RED restart with cache clear
- **Reload time:** ~3-5 seconds
- **Module cache:** Automatically cleared on restart

### Development Configuration
The `python-backend/config.dev.yaml` file provides:
- Debug logging enabled
- Extended timeouts for debugging
- Test data support
- Performance profiling
- Debug image saving

## Features

### Color-Coded Logs
- 🔴 **ERROR** - Red
- 🟡 **WARN** - Yellow
- 🔵 **INFO** - Cyan
- ⚫ **DEBUG** - Gray
- **[PYTHON]** - Blue prefix
- **[NODE-RED]** - Magenta prefix

### Smart Debouncing
- Prevents multiple rapid restarts
- 2-second debounce for Python changes
- 3-second debounce for Node-RED changes

### Graceful Shutdown
- Press `Ctrl+C` to stop all services cleanly
- Automatic cleanup of background processes
- PID tracking for reliable shutdown

## Workflow Examples

### Python Development
```bash
# Start Python backend only with hot-reload
make dev-python

# Edit any .py file - it auto-reloads!
# Check the terminal for reload messages
```

### Node-RED Development
```bash
# Start Node-RED with file watching
make dev-nodered

# Edit node files in node-red/nodes/
# Node-RED restarts automatically
```

### Full Stack Development
```bash
# Start everything with auto-reload
make dev

# Python changes reload in ~1 second
# Node-RED changes restart in ~3 seconds
# All logs are color-coded in one terminal
```

### Split-Screen with tmux
```bash
# Install tmux first
sudo apt-get install tmux

# Start in split-screen mode
make dev-tmux

# You get 3 panes:
# - Python backend output
# - Node-RED output
# - Combined logs
```

## Troubleshooting

### inotify-tools not installed
```bash
sudo apt-get update
sudo apt-get install inotify-tools
```

### Too many open files error
Increase inotify watches limit:
```bash
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Services not reloading
1. Check if inotify-tools is installed: `which inotifywait`
2. Verify file permissions
3. Check logs for errors: `make dev-logs`

### Port already in use
```bash
make stop  # Stop all services
make dev   # Restart in dev mode
```

## Tips

1. **Use config.dev.yaml** for development-specific settings
2. **Check Swagger UI** at http://localhost:8000/docs for API testing
3. **Monitor performance** - dev mode includes profiling
4. **Debug images** are saved to `python-backend/debug/` in dev mode
5. **Combine with VS Code** - The dev mode works great with VS Code's debugger

## Environment Variables

- `MV_CONFIG_FILE` - Override config file path
- `NODE_ENV=development` - Enable development features
- `DEBUG=*` - Enable all debug output for Node-RED

## Performance

- Python hot-reload: ~1-2 seconds
- Node-RED restart: ~3-5 seconds
- File watching overhead: Minimal (<1% CPU)
- Memory usage: Similar to production

The enhanced development mode significantly speeds up the development cycle by eliminating manual restarts!