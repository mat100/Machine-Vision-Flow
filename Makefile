# Machine Vision Flow - Makefile

.PHONY: help install start stop restart status logs clean test dev reload reload-backend reload-nodered reinstall reinstall-backend reinstall-nodered

help:
	@echo "Machine Vision Flow - Available Commands"
	@echo "========================================"
	@echo ""
	@echo "Basic Operations:"
	@echo "  make install    - Install dependencies"
	@echo "  make start      - Start all services"
	@echo "  make stop       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make status     - Show service status"
	@echo "  make logs       - View logs"
	@echo ""
	@echo "Development - Code Changes:"
	@echo "  make reload-backend   - Reload Python backend after code changes"
	@echo "  make reload-nodered   - Reload Node-RED after code changes"
	@echo "  make reload           - Reload both services after code changes"
	@echo ""
	@echo "Development - New Dependencies:"
	@echo "  make reinstall-backend  - Reinstall Python packages (requirements.txt)"
	@echo "  make reinstall-nodered  - Reinstall Node-RED nodes (package.json)"
	@echo "  make reinstall          - Reinstall all dependencies"
	@echo ""
	@echo "Other:"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean logs and temp files"
	@echo "  make dev        - Start in development mode"

install:
	@echo "Installing dependencies..."
	@chmod +x scripts/*.sh services/*.sh
	@cd python-backend && python3 -m venv venv && \
		./venv/bin/pip install -r requirements.txt
	@cd ~/.node-red && npm install $(PWD)/node-red && \
		npm install node-red-contrib-image-output
	@echo "Installation complete!"

start:
	@./scripts/start.sh

stop:
	@./scripts/stop.sh

restart:
	@./scripts/restart.sh

status:
	@./scripts/status.sh

logs:
	@./scripts/logs.sh

clean:
	@echo "Cleaning up..."
	@rm -f python-backend/*.log python-backend/*.pid
	@rm -f *.log *.pid
	@rm -rf python-backend/__pycache__
	@rm -rf python-backend/**/__pycache__
	@find . -name "*.pyc" -delete
	@echo "Cleanup complete!"

# Development mode
dev:
	@echo "Starting in development mode..."
	@./scripts/start.sh --follow

# Testing
test:
	@echo "Running tests..."
	@python3 scripts/test_camera_list.py
	@cd python-backend && ./venv/bin/python -m pytest tests/ -v

# System service installation (requires sudo)
install-services:
	@sudo ./services/install.sh

uninstall-services:
	@sudo ./services/uninstall.sh

# Development shortcuts for code changes (just restart)
reload-backend:
	@echo "Reloading Python backend after code changes..."
	@if [ -f python-backend/backend.pid ]; then \
		PID=$$(cat python-backend/backend.pid); \
		if ps -p $$PID > /dev/null 2>&1; then \
			kill $$PID; \
			sleep 1; \
		fi; \
	fi
	@cd python-backend && \
		source venv/bin/activate && \
		nohup python3 main.py > backend.log 2>&1 & \
		echo $$! > backend.pid
	@echo "Backend reloaded! Check logs: make logs"

reload-nodered:
	@echo "Reloading Node-RED after code changes..."
	@if [ -f node-red.pid ]; then \
		PID=$$(cat node-red.pid); \
		if ps -p $$PID > /dev/null 2>&1; then \
			kill $$PID; \
			sleep 2; \
		fi; \
	fi
	@nohup node-red > node-red.log 2>&1 & echo $$! > node-red.pid
	@echo "Node-RED reloaded!"

reload: reload-backend reload-nodered
	@echo "All services reloaded!"

# Development reinstall for new dependencies
reinstall-backend:
	@echo "Reinstalling Python dependencies..."
	@cd python-backend && ./venv/bin/pip install -r requirements.txt
	@make reload-backend

reinstall-nodered:
	@echo "Reinstalling Node-RED nodes..."
	@cd ~/.node-red && npm install $(PWD)/node-red
	@make reload-nodered

reinstall: reinstall-backend reinstall-nodered
	@echo "All dependencies reinstalled and services reloaded!"

