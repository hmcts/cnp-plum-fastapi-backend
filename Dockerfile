# syntax=docker/dockerfile:1

# ---- Builder: install app and dependencies ----
# renovate: datasource=docker depName=python
FROM python:3.13-slim-trixie AS builder
# renovate: datasource=github-releases depName=astral-sh/uv
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /bin/
WORKDIR /build
COPY pyproject.toml .
COPY app/ app/
RUN uv pip install \
      --no-cache \
      --target=/opt/deps \
      --python /usr/local/bin/python3.13 \
      --index-url https://pypi.org/simple \
      .

# ---- Final: HMCTS distroless base (App Insights pre-wired) ----
# renovate: datasource=docker depName=hmctsprod.azurecr.io/base/python
FROM hmctsprod.azurecr.io/base/python:3.13-distroless

COPY --from=builder /opt/deps /opt/deps
ENV PYTHONPATH=/opt/otel:/opt/deps

CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

