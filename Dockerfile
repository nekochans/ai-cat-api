FROM python:3.11.3-slim AS build

RUN apt-get update && apt-get install -y ca-certificates

FROM python:3.11.3-slim

WORKDIR /src

COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir --upgrade pip && \
  pip install --no-cache-dir "poetry==1.5.1"

RUN poetry config virtualenvs.create false && \
  poetry install --no-interaction --no-ansi --no-root

COPY ./src/ .

EXPOSE 5000

ENV SSL_CERT_PATH /etc/ssl/certs/ca-certificates.crt

COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
