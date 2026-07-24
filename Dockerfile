# ---- Builder: install app and dependencies ----
# REGISTRY_NAME is supplied by the pipeline (az acr build --build-arg); defaults to hmctsprod for local builds
ARG REGISTRY_NAME=hmctsprod
FROM ${REGISTRY_NAME}.azurecr.io/imported/slim/python:3.13-slim-trixie AS builder
# renovate: datasource=github-releases depName=astral-sh/uv
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/
ENV UV_MALWARE_CHECK=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync \
      --locked \
      --no-dev \
      --no-install-project \
      --python /usr/local/bin/python3.13 && \
    cp -r .venv/lib/python3.13/site-packages /opt/deps

# ---- Final: HMCTS distroless base (App Insights pre-wired) ----
FROM ${REGISTRY_NAME}.azurecr.io/base/python:3.13-distroless

COPY --from=builder /opt/deps /opt/deps
COPY app/ /opt/app/app/
COPY pyproject.toml /opt/app/
ENV PYTHONPATH=/opt/otel:/opt/deps

CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
