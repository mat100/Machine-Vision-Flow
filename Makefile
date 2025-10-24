SHELL := /bin/bash

PROJECT_ROOT := $(CURDIR)
SCRIPTS_DIR := $(PROJECT_ROOT)/scripts
BACKEND_DIR := $(PROJECT_ROOT)/python-backend
BACKEND_VENV := $(BACKEND_DIR)/venv
BACKEND_PYTHON := $(BACKEND_VENV)/bin/python

# Runtime directories (fallback to project var/ for development)
LOG_DIR ?= $(PROJECT_ROOT)/var/log
RUN_DIR ?= $(PROJECT_ROOT)/var/run

BACKEND_PID_FILE := $(RUN_DIR)/backend.pid
BACKEND_LOG_FILE := $(LOG_DIR)/backend.log
NODE_RED_PID_FILE := $(RUN_DIR)/node-red.pid
NODE_RED_LOG_FILE := $(LOG_DIR)/node-red.log
PYTHON := python3
PORT_BACKEND := 8000
PORT_NODERED := 1880

ARGS ?=

.PHONY: help install start stop status test clean dev dev-python dev-nodered reload logs

help:
	@echo "Machine Vision Flow - Core Commands"
	@echo "===================================="
	@echo ""
	@echo "  make install       Install dependencies"
	@echo "  make start         Start services"
	@echo "  make stop          Stop services"
	@echo "  make status        Show status"
	@echo "  make test          Run tests"
	@echo "  make clean         Clean temp files"
	@echo ""
	@echo "  make dev           Dev mode (both services)"
	@echo "  make dev-python    Dev mode (Python only)"
	@echo "  make dev-nodered   Dev mode (Node-RED only)"
	@echo "  make reload        Reload services"
	@echo "  make logs          View logs"

install:
	@echo "Installing dependencies..."
	@chmod +x $(SCRIPTS_DIR)/*.sh $(SCRIPTS_DIR)/lib/*.sh
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; ensure_python_backend_env false"
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; ensure_node_red_dependencies false"
	@echo "Installation complete!"

start:
	@$(SCRIPTS_DIR)/start.sh $(ARGS)

stop:
	@$(SCRIPTS_DIR)/stop.sh $(ARGS)

status:
	@$(SCRIPTS_DIR)/status.sh $(ARGS)

logs:
	@if [ -f $(BACKEND_LOG_FILE) ] || [ -f $(NODE_RED_LOG_FILE) ]; then \
		tail -f $(BACKEND_LOG_FILE) $(NODE_RED_LOG_FILE) 2>/dev/null; \
	else \
		echo "No log files found. Start services first with: make start"; \
	fi

clean:
	@echo "Cleaning up..."
	@rm -f $(BACKEND_LOG_FILE) $(BACKEND_PID_FILE)
	@rm -f $(NODE_RED_LOG_FILE) $(NODE_RED_PID_FILE)
	@rm -f $(PROJECT_ROOT)/*.log $(PROJECT_ROOT)/*.pid
	@find $(BACKEND_DIR) -type d -name "__pycache__" -prune -exec rm -rf {} +
	@find $(PROJECT_ROOT) -name "*.pyc" -delete
	@echo "Cleanup complete!"

dev:
	@$(SCRIPTS_DIR)/dev.sh $(ARGS)

dev-python:
	@$(SCRIPTS_DIR)/dev.sh --watch python $(ARGS)

dev-nodered:
	@$(SCRIPTS_DIR)/dev.sh --watch nodered $(ARGS)

reload:
	@echo "Reloading services..."
	@$(MAKE) --no-print-directory stop
	@sleep 2
	@$(MAKE) --no-print-directory start

test:
	@echo "Running tests..."
	@$(SHELL) -lc "source \"$(SCRIPTS_DIR)/lib/services.sh\"; ensure_python_backend_env false"
	@if [ -d $(BACKEND_DIR)/tests ]; then \
		cd $(BACKEND_DIR) && $(BACKEND_PYTHON) -m pytest tests/ -v; \
	else \
		echo "No backend tests found in $(BACKEND_DIR)/tests"; \
	fi
