.PHONY: lint format typecheck lint-container format-container test-container typecheck-container ci run

lint:
	rye run ruff check

format:
	rye run ruff format

typecheck:
	rye run mypy --strict

lint-container:
	docker compose exec ai-cat-api bash -c "cd / && ruff check src/ tests/"

format-container:
	docker compose exec ai-cat-api bash -c "cd / && ruff format"

test-container:
	docker compose exec ai-cat-api bash -c "cd / && pytest -vv -s src/ tests/"

typecheck-container:
	docker compose exec ai-cat-api bash -c "cd / && mypy --strict"

ci: lint-container typecheck-container test-container
	docker compose exec ai-cat-api bash -c "cd / && ruff format --check src/ tests/"

run:
	rye run python src/main.py
