# Development Mode Guide

## Quick Start

1. **Optional tools (for advanced features):**
   ```bash
   sudo apt-get install inotify-tools tmux
   # inotify-tools - for Node-RED file watching
   # tmux - for split-screen mode
   ```

2. **Start development mode:**
   ```bash
   make dev
   ```

## Available Commands

### Basic Development Modes
- `make dev` - Start both services with monitoring
- `make dev-python` - Python backend only
- `make dev-nodered` - Node-RED only with file watching
- `make logs` - View combined logs from both services

### Options for `make dev`
```bash
make dev                         # Default: Node-RED file watching enabled
make dev ARGS="--no-reload"      # Disable file watching
make dev ARGS="--watch python"   # Python only (no auto-reload)
make dev ARGS="--watch nodered"  # Node-RED with file watching
make dev ARGS="--watch none"     # No file watching
make dev ARGS="--no-color"       # Disable colored logs
make dev ARGS="--tmux"           # Use tmux split-screen
make dev ARGS="--vscode"         # Setup VSCode port forwarding
```

## How It Works

### Python Backend
- **Reload method:** **Manual restart required**
- **Command:** `make reload` to restart both services
- **Config:** Uses `config.dev.yaml` if available (auto-loaded)
- **Development:** Run with `python main.py` directly for debugging

**Note:** Python backend does NOT auto-reload on file changes. Use `make reload` after making changes, or run `python main.py` directly for faster iteration.

### Node-RED Auto-Restart
- **Monitored files:** `*.js`, `*.html`, `*.json` in `node-red/nodes/`
- **Reload method:** Full Node-RED restart with cache clear
- **Reload time:** ~3-5 seconds
- **Module cache:** Automatically cleared on restart
- **Requires:** `inotify-tools` installed

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
# Start Python backend only
make dev-python

# Edit .py files, then reload:
make reload

# Or run directly for debugging:
cd python-backend
source venv/bin/activate
python main.py
```

### Node-RED Development
```bash
# Start Node-RED with file watching
make dev-nodered

# Edit node files in node-red/nodes/
# Node-RED restarts automatically (~3-5s)
```

### Full Stack Development
```bash
# Start both services
make dev

# Python changes: make reload (manual)
# Node-RED changes: auto-restart (~3-5s)
# All logs are color-coded in one terminal
```

### Split-Screen with tmux
```bash
# Install tmux first
sudo apt-get install tmux

# Start in split-screen mode
make dev ARGS="--tmux"

# You get 3 panes:
# - Python backend output
# - Node-RED output
# - Combined logs

# Detach: Ctrl+b, d
# Reattach: tmux attach -t mvflow-dev
```

### VSCode Integration
```bash
# Enable VSCode port forwarding detection
make dev ARGS="--vscode"

# VSCode will automatically forward:
# - Port 8000 (Python Backend)
# - Port 1880 (Node-RED)
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

### Node-RED not auto-restarting
1. Check if inotify-tools is installed: `which inotifywait`
2. Verify file permissions in `node-red/nodes/`
3. Check logs for errors: `make logs`

### Python changes not applying
Python backend requires **manual restart**:
```bash
make reload
```

### Port already in use
```bash
make stop  # Stop all services
make dev   # Restart in dev mode
```

## Tips

1. **Use config.dev.yaml** for development-specific settings
2. **Check Swagger UI** at http://localhost:8000/docs for API testing
3. **Use `make reload`** after Python changes (no auto-reload)
4. **Node-RED auto-restarts** when you edit custom nodes
5. **Combine with VS Code** - Use `make dev ARGS="--vscode"` for port forwarding
6. **View logs** with `make logs` for real-time monitoring

## Environment Variables

- `MV_CONFIG_FILE` - Override config file path (defaults to `config.dev.yaml` in dev mode)
- `LOG_DIR` - Override log directory (defaults to `var/log/`)
- `RUN_DIR` - Override PID directory (defaults to `var/run/`)
- `DEBUG=*` - Enable all debug output for Node-RED

## Performance

- Python restart: Manual (`make reload` takes ~2-3 seconds)
- Node-RED auto-restart: ~3-5 seconds (when file changes detected)
- File watching overhead: Minimal (<1% CPU)
- Memory usage: Similar to production

## Comparison: Dev vs Production

| Feature | Development (`make dev`) | Production (`systemd`) |
|---------|-------------------------|------------------------|
| Python reload | Manual (`make reload`) | Restart service |
| Node-RED reload | Auto (file watching) | Restart service |
| Logs | `var/log/` in project | `/var/log/machinevisionflow/` |
| PIDs | `var/run/` in project | `/run/machinevisionflow/` |
| Config | `config.dev.yaml` | `config.yaml` |
| User | Current user | Service user (cnc) |