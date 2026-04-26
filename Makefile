.PHONY: help setup backend frontend docker-up docker-down

VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

setup:         ## Install backend + frontend dependencies
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt
	cd frontend && npm install

backend:       ## Run the FastAPI backend in dev mode
	cd backend && $(shell pwd)/$(VENV)/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:      ## Run the Vite frontend in dev mode
	cd frontend && npm run dev

docker-up:     ## Start all services with docker-compose
	cp -n .env.example .env || true
	docker-compose up --build

docker-down:   ## Stop all docker-compose services
	docker-compose down

lint-backend:  ## Lint the backend with ruff (if installed)
	cd backend && $(shell pwd)/$(VENV)/bin/ruff check . || true

test-backend:  ## Run backend tests with pytest (if tests exist)
	cd backend && $(shell pwd)/$(VENV)/bin/pytest -q || true
