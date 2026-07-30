.PHONY: dev build up down logs clean restart install lint typecheck test

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

clean:
	docker compose down -v --remove-orphans

restart:
	docker compose restart

install:
	pip install -e '.[api,dev]'

lint:
	ruff check .

typecheck:
	mypy src/spectral_matching

test:
	python3 -m pytest tests/ -v

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

frontend-dev:
	cd frontend && npm run dev
