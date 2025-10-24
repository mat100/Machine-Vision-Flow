# VSCode Configuration for Machine Vision Flow

This directory contains VSCode workspace configuration for optimal development experience.

## Quick Start

1. **Install recommended extensions** (VSCode will prompt you)
2. **Run dev mode** using Task: `Ctrl+Shift+P` → "Tasks: Run Task" → "Start Dev Mode"
3. **Ports auto-forward** - Check the "Ports" tab (should auto-forward 8000 and 1880)

## Files Overview

### `tasks.json` - Development Tasks
Available tasks (press `Ctrl+Shift+P` → "Tasks: Run Task"):
- **Start Dev Mode** - Start both services with auto-reload
- **Start Dev Mode (Python only)** - Python backend only
- **Start Dev Mode (Node-RED only)** - Node-RED only
- **Stop Services** - Stop all services
- **Run Tests** - Run pytest (`Ctrl+Shift+T`)
- **Format Code** - Run black + isort
- **Lint Code** - Run flake8

### `launch.json` - Debugging
Debug configurations (press `F5` or select from dropdown):

**Recommended:**
- **Debug: Full Stack (Python + Node-RED)** ⭐ - Start both services with Python debugging

**Individual Services:**
- **Debug: Python Backend Only** - Debug FastAPI backend only
- **Start: Node-RED** - Start Node-RED without debugging

**Testing:**
- **Python: Current File** - Debug currently open Python file
- **Python: Pytest Current File** - Debug current test file
- **Python: All Tests** - Debug all tests

### `settings.json` - Workspace Settings
- Python interpreter: `python-backend/venv/bin/python`
- Auto-format on save with black (line length 100)
- Auto-organize imports with isort
- Flake8 linting enabled
- **Auto port forwarding** for remote development

### `extensions.json` - Recommended Extensions
Core extensions:
- Python + Pylance (language support)
- Black Formatter + isort (formatting)
- Flake8 (linting)
- Node-RED (for flows)
- GitLens (git integration)

## Port Forwarding

### Local Development
Ports are available at:
- http://localhost:8000 - Python Backend API
- http://localhost:8000/docs - Swagger UI
- http://localhost:1880 - Node-RED

### Remote Development (SSH/WSL)
VSCode will **automatically forward** ports 8000 and 1880.

Check the **Ports** tab (bottom panel) to see forwarded ports.

You can also manually forward ports:
1. Open Ports tab
2. Click "Forward a Port"
3. Enter port number

## Keyboard Shortcuts

- `F5` - Start debugging (FastAPI)
- `Ctrl+Shift+T` - Run tests
- `Ctrl+Shift+B` - Run build task
- `Ctrl+Shift+P` - Command palette (run tasks)
- `Shift+Alt+F` - Format document

## Tips

1. **Testing**: Use the Test Explorer sidebar for interactive test running
2. **Debugging**: Set breakpoints with `F9`, step with `F10/F11`
3. **Port Issues**: If ports don't auto-forward, manually add them in Ports tab
4. **Problems Panel**: View linting errors (`Ctrl+Shift+M`)

## Troubleshooting

### Port forwarding not working
1. Check if ports are already in use: `make status`
2. Manually forward in Ports tab
3. Restart VSCode
4. Check `remote.autoForwardPorts` setting is `true`

### Python interpreter not found
1. Run: `make install` to create venv
2. Select interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter"
3. Choose `python-backend/venv/bin/python`

### Tests not discovered
1. Ensure pytest is installed: `pip install -r requirements-dev.txt`
2. Reload window: `Ctrl+Shift+P` → "Developer: Reload Window"
