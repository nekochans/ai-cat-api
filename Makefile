.PHONY: lint format typecheck lint-container format-container test-container typecheck-container ci run

lint:
	rye run flake8 src/ tests/

format:
	rye run black src/ tests/

typecheck:
	rye run mypy --strict

lint-container:
	docker compose exec ai-cat-api bash -c "cd / && flake8 src/ tests/"

format-container:
	docker compose exec ai-cat-api bash -c "cd / && black src/ tests/"

test-container:
	docker compose exec ai-cat-api bash -c "cd / && pytest -vv -s src/ tests/"

typecheck-container:
	docker compose exec ai-cat-api bash -c "cd / && mypy --strict"

ci: lint-container typecheck-container test-container
	docker compose exec ai-cat-api bash -c "cd / && black --check src/ tests/"

run:
	rye run python src/main.py
