FROM python:3.11.3-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir --upgrade pip && \
  pip install --no-cache-dir "poetry==1.5.1"

RUN poetry config virtualenvs.create false && \
  poetry install --no-interaction --no-ansi --no-root

COPY . .

EXPOSE 5000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
