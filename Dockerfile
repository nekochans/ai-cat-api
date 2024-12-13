FROM python:3.12.4-slim AS build

RUN apt-get update && apt-get install -y ca-certificates

FROM python:3.12.4-slim

WORKDIR /src

RUN apt-get update && \
  apt-get install -y --no-install-recommends build-essential && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

COPY pyproject.toml pyproject.toml ./
COPY uv.lock uv.lock ./

COPY --from=ghcr.io/astral-sh/uv:0.5.8 /uv /bin/uv

COPY ./src/ .

RUN uv export -o requirements.txt --no-hashes

RUN pip install --no-cache-dir --upgrade -r requirements.txt

EXPOSE 5000

ENV SSL_CERT_PATH /etc/ssl/certs/ca-certificates.crt

COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
