# renovate: datasource=docker depName=python
FROM python:3.13-slim-trixie AS build
RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends --yes gcc libc6-dev && \
    ln -s /usr/local/bin/python /usr/bin/python && \
    /usr/bin/python -m venv /venv && \
    /venv/bin/pip install --upgrade pip setuptools wheel

COPY pyproject.toml .
RUN /venv/bin/pip install --disable-pip-version-check .

# renovate: datasource=docker depName=hmctsprod.azurecr.io/base/python
FROM hmctsprod.azurecr.io/base/python:3.13-distroless
COPY --from=build /venv /venv
COPY app/ /app/
WORKDIR /app
ENTRYPOINT ["/venv/bin/python3"]
CMD ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
