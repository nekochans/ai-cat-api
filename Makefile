.PHONY: lint format typecheck lint-container format-container test-container typecheck-container ci run

lint:
	uv run ruff check

format:
	uv run ruff format

typecheck:
	uv run mypy --strict

run:
	uv run python src/main.py

lint-container:
	docker compose exec ai-cat-api bash -c "cd / && ruff check --output-format=github src/ tests/"

format-container:
	docker compose exec ai-cat-api bash -c "cd / && ruff format"

test-container:
	docker compose exec ai-cat-api bash -c "cd / && pytest -vv -s src/ tests/"

typecheck-container:
	docker compose exec ai-cat-api bash -c "cd / && mypy --strict"

ci: lint-container typecheck-container test-container
	docker compose exec ai-cat-api bash -c "cd / && ruff format src/ tests/ --check --diff"
