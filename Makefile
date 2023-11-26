.PHONY: lint format ci

lint:
	flake8 .

format:
	black .

typecheck:
	poetry run python -m mypy --strict

test:
	poetry run python -m pytest -vv

lint-container:
	docker compose exec ai-cat-api bash -c "cd / && poetry run flake8 src/ tests/"

format-container:
	docker compose exec ai-cat-api bash -c "cd / && poetry run black src/ tests/"

test-container:
	docker compose exec ai-cat-api bash -c "cd / && poetry run python -m pytest -vv -s"

typecheck-container:
	docker compose exec ai-cat-api bash -c "cd / && poetry run python -m mypy --strict"

ci: test typecheck
	poetry run flake8 .
	poetry run black --check .

run:
	python src/main.py
