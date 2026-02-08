.PHONY: help build up down logs clean restart migrate test bootstrap-veos

help:
	@echo "Arista vEOS Connector - Makefile Commands"
	@echo ""
	@echo "  make build      - Build all Docker images"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - Show logs from all services"
	@echo "  make clean      - Remove containers, volumes, and images"
	@echo "  make restart    - Restart all services"
	@echo "  make migrate    - Run database migrations"
	@echo "  make test       - Run backend tests"
	@echo "  make bootstrap-veos - Bootstrap real vEOS devices"

# Try docker compose (new) first, fallback to docker-compose (old)
DOCKER_COMPOSE = $(shell command -v docker-compose 2> /dev/null || echo "docker compose")

build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d
	@echo "Services starting... Use 'make logs' to view logs"

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

clean:
	$(DOCKER_COMPOSE) down -v --rmi all
	@echo "All containers, volumes, and images removed"

restart:
	$(DOCKER_COMPOSE) restart

migrate:
	$(DOCKER_COMPOSE) exec backend python -m alembic upgrade head

test:
	$(DOCKER_COMPOSE) exec backend pytest

test-backend:
	$(DOCKER_COMPOSE) exec backend pytest tests/ -v

test-collector:
	$(DOCKER_COMPOSE) exec backend pytest tests/test_collector.py -v -s

test-mqtt:
	$(DOCKER_COMPOSE) exec backend pytest tests/test_mqtt.py -v -s

test-e2e:
	cd frontend && npm install && npx playwright test

bootstrap-veos:
	$(DOCKER_COMPOSE) exec backend python scripts/bootstrap_real_veos.py
