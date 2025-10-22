SHELL := /bin/bash

PROJECT_ROOT := $(CURDIR)
SCRIPTS_DIR := $(PROJECT_ROOT)/scripts
BACKEND_DIR := $(PROJECT_ROOT)/python-backend
BACKEND_VENV := $(BACKEND_DIR)/venv
BACKEND_PYTHON := $(BACKEND_VENV)/bin/python
BACKEND_PID_FILE := $(BACKEND_DIR)/backend.pid
BACKEND_LOG_FILE := $(BACKEND_DIR)/backend.log
NODE_RED_PID_FILE := $(PROJECT_ROOT)/node-red.pid
NODE_RED_LOG_FILE := $(PROJECT_ROOT)/node-red.log
PYTHON := python3
PORT_BACKEND := 8000
PORT_NODERED := 1880

ARGS ?=

.PHONY: help install install-backend install-nodered start stop restart status logs clean test dev dev-python dev-nodered dev-tmux dev-watch dev-logs reload reload-backend reload-nodered reinstall reinstall-backend reinstall-nodered

help:
	@printf "Machine Vision Flow - Available Commands\n"
	@printf "========================================\n\n"
	@printf "Basic Operations:\n"
	@printf "  make install    - Install dependencies\n"
	@printf "  make start      - Start all services\n"
	@printf "  make stop       - Stop all services\n"
	@printf "  make restart    - Restart all services\n"
	@printf "  make status     - Show service status\n"
	@printf "  make logs       - View logs\n\n"
	@printf "Development - Code Changes:\n"
	@printf "  make reload-backend   - Reload Python backend after code changes\n"
	@printf "  make reload-nodered   - Reload Node-RED after code changes\n"
	@printf "  make reload           - Reload both services after code changes\n\n"
	@printf "Development - New Dependencies:\n"
	@printf "  make reinstall-backend  - Reinstall Python packages (requirements.txt)\n"
	@printf "  make reinstall-nodered  - Reinstall Node-RED nodes (package.json)\n"
	@printf "  make reinstall          - Reinstall all dependencies\n\n"
	@printf "Enhanced Development:\n"
	@printf "  make dev             - Enhanced dev mode with auto-reload\n"
	@printf "  make dev-python      - Run only Python backend with hot-reload\n"
	@printf "  make dev-nodered     - Run only Node-RED with file watching\n"
	@printf "  make dev-tmux        - Dev mode with tmux split-screen\n"
	@printf "  make dev-watch       - Watch files without starting services\n"
	@printf "  make dev-logs        - Show colored, filtered logs\n\n"
	@printf "Other:\n"
	@printf "  make test            - Run tests\n"
	@printf "  make clean           - Clean logs and temp files\n"

install: install-backend install-nodered
	@chmod +x $(SCRIPTS_DIR)/*.sh
	@echo "Installation complete!"

install-backend:
	@echo "Installing Python backend dependencies..."
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; ensure_python_backend_env false"

install-nodered:
	@echo "Installing Node-RED dependencies..."
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; ensure_node_red_dependencies false"

start:
	@$(SCRIPTS_DIR)/start.sh $(ARGS)

stop:
	@$(SCRIPTS_DIR)/stop.sh $(ARGS)

restart:
	@$(SCRIPTS_DIR)/restart.sh $(ARGS)

status:
	@$(SCRIPTS_DIR)/status.sh $(ARGS)

logs:
	@$(SCRIPTS_DIR)/logs.sh $(ARGS)

clean:
	@echo "Cleaning up..."
	@rm -f $(BACKEND_LOG_FILE) $(BACKEND_PID_FILE)
	@rm -f $(NODE_RED_LOG_FILE) $(NODE_RED_PID_FILE)
	@rm -f $(PROJECT_ROOT)/*.log $(PROJECT_ROOT)/*.pid
	@find $(BACKEND_DIR) -type d -name "__pycache__" -prune -exec rm -rf {} +
	@find $(PROJECT_ROOT) -name "*.pyc" -delete
	@echo "Cleanup complete!"

dev:
	@chmod +x $(SCRIPTS_DIR)/dev.sh 2>/dev/null || true
	@$(SCRIPTS_DIR)/dev.sh $(ARGS)

dev-python:
	@chmod +x $(SCRIPTS_DIR)/dev-python.sh 2>/dev/null || true
	@$(SCRIPTS_DIR)/dev-python.sh $(ARGS)

dev-nodered:
	@chmod +x $(SCRIPTS_DIR)/dev-nodered.sh 2>/dev/null || true
	@$(SCRIPTS_DIR)/dev-nodered.sh $(ARGS)

dev-tmux:
	@chmod +x $(SCRIPTS_DIR)/dev.sh 2>/dev/null || true
	@$(SCRIPTS_DIR)/dev.sh --tmux $(ARGS)

dev-watch:
	@echo "Starting file watchers only (services must be running)..."
	@chmod +x $(SCRIPTS_DIR)/lib/watchers.sh 2>/dev/null || true
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/watchers.sh\"; source \"$(SCRIPTS_DIR)/lib/services.sh\"; start_watchers true true true"

dev-logs:
	@echo "Showing colored, filtered logs..."
	@if [ -f $(BACKEND_LOG_FILE) ] && [ -f $(NODE_RED_LOG_FILE) ]; then \
		tail -f $(BACKEND_LOG_FILE) $(NODE_RED_LOG_FILE) | awk '\
			/ERROR/ {print "\033[31m" $$0 "\033[0m"; next} \
			/WARN/ {print "\033[33m" $$0 "\033[0m"; next} \
			/INFO/ {print "\033[36m" $$0 "\033[0m"; next} \
			/DEBUG/ {print "\033[90m" $$0 "\033[0m"; next} \
			/backend\.log/ {print "\033[34m[PYTHON]\033[0m " $$0; next} \
			/node-red\.log/ {print "\033[35m[NODE-RED]\033[0m " $$0; next} \
			{print $$0}'; \
	else \
		echo "Log files not found. Start services first."; \
	fi

test:
	@echo "Running tests..."
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; ensure_python_backend_env false"
	@if [ -f $(SCRIPTS_DIR)/test_camera_list.py ]; then \
		$(PYTHON) $(SCRIPTS_DIR)/test_camera_list.py; \
	fi
	@if [ -d $(BACKEND_DIR)/tests ]; then \
		cd $(BACKEND_DIR) && $(BACKEND_PYTHON) -m pytest tests/ -v; \
	else \
		echo "No backend tests found in $(BACKEND_DIR)/tests"; \
	fi

reload-backend:
	@echo "Reloading Python backend after code changes..."
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; stop_python_backend; start_python_backend; wait_for_port $(PORT_BACKEND) 'Python backend'; pid=$$(cat \"$$BACKEND_PID_FILE\"); log_success \"Backend reloaded (PID: $$pid)\"; log_info 'Check logs with: make logs'"

reload-nodered:
	@echo "Reloading Node-RED after code changes..."
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; stop_node_red; start_node_red; wait_for_port $(PORT_NODERED) 'Node-RED'; pid=$$(cat \"$$NODE_RED_PID_FILE\"); log_success \"Node-RED reloaded (PID: $$pid)\""

reload: reload-backend reload-nodered
	@echo "All services reloaded!"

reinstall-backend:
	@echo "Reinstalling Python dependencies..."
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; ensure_python_backend_env true"
	@$(MAKE) --no-print-directory reload-backend

reinstall-nodered:
	@echo "Reinstalling Node-RED nodes..."
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; ensure_node_red_dependencies true"
	@$(MAKE) --no-print-directory reload-nodered

reinstall: reinstall-backend reinstall-nodered
	@echo "All dependencies reinstalled and services reloaded!"
