.PHONY: lint format ci

lint:
	flake8 .

format:
	black .

typecheck:
	poetry run python -m mypy --strict

lint-container:
	docker compose exec ai-cat-api bash -c "cd / && poetry run flake8 src/ tests/"

format-container:
	docker compose exec ai-cat-api bash -c "cd / && poetry run black src/ tests/"

test-container:
	docker compose exec ai-cat-api bash -c "cd / && poetry run python -m pytest -vv -s"

typecheck-container:
	docker compose exec ai-cat-api bash -c "cd / && poetry run python -m mypy --strict"

ci: lint-container typecheck-container test-container

run:
	python src/main.py
