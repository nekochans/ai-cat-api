.PHONY: lint format ci

lint:
	flake8 .

format:
	black .

ci:
	poetry run flake8 .
	poetry run black --check .
