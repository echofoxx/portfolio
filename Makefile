.PHONY: up down logs test reset backup restore lint
up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f web db
health:
	docker compose ps
	curl -fsS http://localhost:$${APP_PORT:-8080}/health/ready
test:
	docker compose run --rm web pytest -q
reset:
	docker compose down -v
	docker compose up -d --build
backup:
	./scripts/backup.sh
restore:
	./scripts/restore.sh backups/latest.sql.gz
