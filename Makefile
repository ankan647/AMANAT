PY ?= python3.12
PYFALLBACK := $(shell command -v python3.12 >/dev/null 2>&1 && echo python3.12 || echo python3.11)
VENV := backend/.venv
BACKEND_PY := $(VENV)/bin/python
ifeq ($(OS),Windows_NT)
BACKEND_PY := $(VENV)/Scripts/python.exe
endif

.PHONY: doctor install seed dev backend frontend test e2e contract build docker-up lint qa-screens

doctor:
	@echo "Checking prerequisites..."
	@node --version
	@npm --version
	@command -v python3.12 >/dev/null 2>&1 && python3.12 --version || (echo "python3.12 not found, falling back to python3.11" && python3.11 --version)
	@command -v docker >/dev/null 2>&1 && echo "docker: available" || echo "docker: not available (optional)"
	@command -v tesseract >/dev/null 2>&1 && echo "tesseract: available" || echo "tesseract: not available (optional, OCR skipped)"

install:
	cd backend && $(PYFALLBACK) -m venv .venv
	cd backend && . .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate; pip install -U pip && pip install -e ".[dev]"
	cd frontend && npm install

seed:
	cd backend && $(BACKEND_PY) -m app.seed

dev:
	$(MAKE) backend & $(MAKE) frontend & wait

backend:
	cd backend && $(BACKEND_PY) -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && $(BACKEND_PY) -m pytest
	cd frontend && npm run test

e2e:
	cd frontend && npm run e2e

contract:
	cd backend && $(BACKEND_PY) -m app.export_openapi
	cd frontend && npm run gen:types

build:
	cd frontend && npm run build

docker-up:
	docker compose up --build

lint:
	cd backend && $(BACKEND_PY) -m ruff check .
	cd frontend && npm run lint

qa-screens:
	cd frontend && npm run qa-screens
