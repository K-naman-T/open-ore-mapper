.PHONY: dev build up down logs ps clean restart
.PHONY: install lint typecheck test test-emit test-e2e test-all
.PHONY: frontend-install frontend-lint frontend-build frontend-e2e
.PHONY: check-all

# ─── Development (Docker) ──────────────────────────────────────────
# Starts backend on port 8000 only.  Frontend runs via `cd frontend && npm run dev`.

dev:
	docker compose up --build -d

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

restart:
	docker compose restart

# ─── Backend ───────────────────────────────────────────────────────

install:
	uv sync --all-extras

lint:
	ruff check .

typecheck:
	mypy src/open_ore_mapper

test:
	python3 -m pytest -v --ignore=tests/test_e2e_mineral_detection.py --ignore=tests/test_emit_client.py

test-emit:
	python3 -m pytest -v tests/test_emit_client.py

test-e2e:
	python3 -m pytest -v tests/test_e2e_mineral_detection.py

test-all: test test-emit test-e2e

check-all: lint typecheck test-all

# ─── Frontend ──────────────────────────────────────────────────────

frontend-install:
	cd frontend && npm install

frontend-lint:
	cd frontend && npm run lint

frontend-build:
	cd frontend && npm run build

frontend-e2e:
	cd frontend && npm run test:e2e
