# Makefile for Album Catalog Docker Development
.PHONY: help up down restart build logs shell migrate test import clean

help: ## Show this help message
	@echo "Album Catalog - Docker Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services (PostgreSQL + Django)
	docker-compose up -d
	@echo "Services starting... Run 'make logs' to view output"

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

build: ## Build/rebuild Docker images
	docker-compose build

logs: ## View logs from all services
	docker-compose logs -f

logs-db: ## View PostgreSQL logs only
	docker-compose logs -f db

logs-web: ## View Django logs only
	docker-compose logs -f web

shell: ## Open Django shell in web container
	docker-compose exec web python manage.py shell

bash: ## Open bash shell in web container
	docker-compose exec web /bin/bash

migrate: ## Run Django migrations
	docker-compose exec web python manage.py migrate

makemigrations: ## Create new migrations
	docker-compose exec web python manage.py makemigrations

createsuperuser: ## Create Django superuser
	docker-compose exec web python manage.py createsuperuser

import: ## Import albums (limit 10 for testing)
	docker-compose exec web python manage.py import_albums --limit 10

import-all: ## Import all albums from Google Sheets
	docker-compose exec web python manage.py import_albums

test: ## Run tests with pytest
	docker-compose exec web pytest tests/ -v

test-cov: ## Run tests with coverage
	docker-compose exec web pytest tests/ --cov=catalog --cov-report=html

psql: ## Connect to PostgreSQL database
	docker-compose exec db psql -U progmetal -d progmetal

db-backup: ## Backup PostgreSQL database
	docker-compose exec db pg_dump -U progmetal progmetal > backup_$(shell date +%Y%m%d_%H%M%S).sql

db-restore: ## Restore PostgreSQL database (usage: make db-restore FILE=backup.sql)
	cat $(FILE) | docker-compose exec -T db psql -U progmetal progmetal

clean: ## Stop services and remove volumes (WARNING: deletes database data)
	docker-compose down -v
	rm -f db.sqlite3

status: ## Show status of all services
	docker-compose ps

prune: ## Remove unused Docker images and containers
	docker system prune -f

# Development workflow shortcuts
dev: up migrate ## Start development environment and run migrations

dev-fresh: clean build up migrate ## Fresh start with clean database

dev-import: dev import ## Start development and import test data
