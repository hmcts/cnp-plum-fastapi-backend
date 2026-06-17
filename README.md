# plum-fastapi-backend

A backend service written in Python using FastAPI

The application exposes health endpoints at `http://localhost:8000/health/readiness` and `http://localhost:8000/health/liveness`.

## Running locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) then:

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

The service will be available at `http://localhost:8000`.

## Running locally via Docker

> **Note:** The Dockerfile uses an HMCTS internal base image from `hmctsprod.azurecr.io`. You must be logged in to the registry (`az acr login --name hmctsprod`) before building.

```bash
docker build -t fastapi-backend .
docker run -p 8000:8000 fastapi-backend
```

## Health endpoints

Your service must expose:

- `GET /health/readiness` — return HTTP 200 when ready to receive traffic
- `GET /health/liveness` — return HTTP 200 when the process is alive

## Running tests

```bash
uv run pytest tests/unit -v          # unit tests
uv run pytest tests/smoke -v         # smoke tests (requires TEST_URL env var)
uv run pytest tests/functional -v    # functional tests (requires TEST_URL env var)
```

## Managing dependencies

Dependencies are managed with [uv](https://docs.astral.sh/uv/). The `uv.lock` file must always be committed — the Docker build uses `--frozen` and will fail if it is missing or out of sync.

### Adding a dependency

```bash
uv add <package>          # production dependency
uv add --dev <package>    # development-only dependency (not installed in Docker)
```

This updates both `pyproject.toml` and `uv.lock`. Commit both files.

### Updating dependencies

```bash
uv sync          # install/update to match uv.lock
uv lock --upgrade  # regenerate uv.lock with latest compatible versions
```

### Supply chain security

`pyproject.toml` sets `exclude-newer = "7 days"` in `[tool.uv]`, which automatically prevents packages released in the last 7 days from being pinned when generating or updating the lockfile. This applies to all `uv lock` and `uv add` runs without any extra flags.

`UV_MALWARE_CHECK=1` is set in the Dockerfile, enabling uv's built-in malware scanning during install.

## Database (PostgreSQL)

To enable PostgreSQL, uncomment the `postgresql` block in `charts/plum-fastapi-backend/values.yaml` and add your database config to the `environment` section.

## Jenkins

This service uses the HMCTS Jenkins shared library. Follow the [new component setup guide](https://hmcts.github.io/cloud-native-platform/new-component/github-repo.html) to register your service.
