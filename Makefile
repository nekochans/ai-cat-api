.PHONY: lint format ci

lint:
	flake8 .

format:
	black .

typecheck:
	poetry run python -m mypy --strict

test:
	poetry run python -m pytest -v

ci: test typecheck
	poetry run flake8 .
	poetry run black --check .

run:
	python src/main.py
