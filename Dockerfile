FROM python:3.12.4-slim AS build

RUN apt-get update && apt-get install -y ca-certificates

FROM python:3.12.4-slim AS development

WORKDIR /src

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential

COPY requirements.lock requirements-dev.lock ./

RUN sed '/-e/d' requirements.lock > requirements.txt && \
    sed '/-e/d' requirements-dev.lock >> requirements.txt && \
    pip install -r requirements.txt

COPY ./src/ .

EXPOSE 5000

ENV SSL_CERT_PATH /etc/ssl/certs/ca-certificates.crt

COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]

FROM python:3.12.4-slim

WORKDIR /src

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential

COPY requirements.lock requirements-dev.lock ./

RUN sed '/-e/d' requirements.lock > requirements.txt && \
  pip install -r requirements.txt

COPY ./src/ .

EXPOSE 5000

ENV SSL_CERT_PATH /etc/ssl/certs/ca-certificates.crt

COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
