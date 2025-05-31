# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI Cat API backend service that provides a conversational AI with cat personality (specifically "Moko"). The system allows guest users to chat with an AI cat character through Server-Sent Events (SSE) streaming responses.

## Architecture

The codebase follows Domain-Driven Design (DDD) with clean architecture patterns:

- **Domain Layer** (`src/domain/`): Core business logic including cat personality definitions, message entities, and repository interfaces
- **Use Case Layer** (`src/usecase/`): Application business logic orchestrating domain services
- **Infrastructure Layer** (`src/infrastructure/`): External service implementations (OpenAI, MySQL via aiomysql)
- **Presentation Layer** (`src/presentation/`): FastAPI controllers, routers, and HTTP handling

## Core Components

- **Cat Personality System**: Each cat (currently only "moko") has a detailed prompt template defining personality, behavior, and speaking patterns
- **Conversation History**: Guest users can maintain conversation context across messages using conversation IDs
- **Streaming Responses**: AI responses are streamed via SSE for real-time chat experience
- **Repository Pattern**: Clean separation between business logic and data persistence/external APIs

## Development Commands

### Setup
```bash
# Install dependencies and create virtual environment
uv sync --frozen

# Start Docker containers (required for database)
docker compose up --build -d
```

### Development Tasks
```bash
# Run linter
make lint

# Format code
make format

# Run type checker
make typecheck

# Start development server (requires MySQL container running)
make run
```

### Testing
```bash
# Run all tests (requires Docker containers)
make test-container

# Run specific test file
docker compose exec ai-cat-api bash -c "cd / && pytest -vv -s tests/path/to/test_file.py"

# Run LLM evaluation tests (expensive, normally skipped)
# Uncomment @pytest.mark.skip in test file first
docker compose exec ai-cat-api bash -c "cd / && pytest -vv -s tests/infrastructure/repository/openai/openai_cat_message_repository/test_generate_message_for_guest_user.py"
```

### Container Development
```bash
# Access container shell
docker compose exec ai-cat-api bash

# Run tasks in container (note: cd to / first)
make lint-container
make format-container
make typecheck-container
make ci  # Run all checks
```

## Testing Guidelines

- Each test creates a unique database name using `create_test_db_name()` from `tests/db/setup_test_database.py`
- Tests run in parallel on GitHub Actions, so avoid fixed database names
- Periodically clean up test databases by recreating containers:
  ```bash
  docker compose down --rmi all --volumes --remove-orphans
  docker compose up --build -d
  ```

## Environment Variables

Required environment variables for development:
- `OPENAI_API_KEY`: OpenAI API access
- `BASIC_AUTH_USERNAME`/`BASIC_AUTH_PASSWORD`: API authentication
- Database configuration: `DB_HOST`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`
- SSL configuration: `SSL_CERT_PATH`
- PlanetScale API tokens for test database schema setup

## API Usage

Test the main endpoint:
```bash
API_CREDENTIAL=`echo -n "$BASIC_AUTH_USERNAME:$BASIC_AUTH_PASSWORD" | base64`
curl -v -N \
-X POST \
-H "Content-Type: application/json" \
-H "Authorization: Basic $API_CREDENTIAL" \
-H "Accept: text/event-stream" \
-d '{"userId": "6a17f37c-996e-7782-fefd-d71eb7eaaa37", "message": "こんにちはもこちゃん🐱"}' \
http://localhost:8000/cats/moko/messages-for-guest-users
```

## Key Files

- `src/domain/cat.py`: Cat personality prompt templates and types
- `src/usecase/generate_cat_message_for_guest_user_use_case.py`: Main conversation flow orchestration
- `src/presentation/router/cats.py`: HTTP endpoints and SSE streaming
- `src/infrastructure/repository/openai/`: OpenAI API integration for message generation
- `src/infrastructure/repository/aiomysql/`: MySQL database operations for conversation history