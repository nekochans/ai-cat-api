.PHONY: lint format ci

lint:
	flake8 .

format:
	black .

test:
	poetry run python -m pytest -v

ci: test
	poetry run flake8 .
	poetry run black --check .

run:
	python src/main.py
