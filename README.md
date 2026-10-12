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

## AI Gateway speech-to-text

`POST /speech-to-text/fast` streams a `multipart/form-data` request to the AI
Gateway fast transcription capability and returns the complete synchronous
response. The request must include an `audio` file and may include a
`definition` field containing transcription options as a JSON string.

This endpoint is currently configured for sandbox only. Set
`AI_GATEWAY_SPEECH_TO_TEXT_URL`,
`AI_GATEWAY_SPEECH_TO_TEXT_SUBSCRIPTION_KEY_FILE` (or
`AI_GATEWAY_SPEECH_TO_TEXT_SUBSCRIPTION_KEY`), and `AI_GATEWAY_SCOPE`.

### Transcribing stored audio

The direct `/speech-to-text/fast` endpoint is unchanged. To store a recording
and transcribe it later:

```bash
curl -X POST http://localhost:8000/speech-to-text/blobs \
  -F 'audio=@recording.wav'
# HTTP 201: {"blob_name":"<generated-id>"}

curl -X POST http://localhost:8000/speech-to-text/fast/blob \
  -H 'Content-Type: application/json' \
  -d '{"blob_name":"<generated-id>","definition":{"locales":["en-GB"]}}'
```

The upload endpoint stores the audio file (not the multipart envelope) under a
unique name and returns `blob_name`. The transcription endpoint retrieves that
blob from the configured container and streams it to the same AI Gateway fast
transcription capability. `definition` is optional and is a JSON object here,
rather than the JSON-string form field used by `/fast`. Existing blobs in the
configured container can also be transcribed by name, including names with `/`.
Gateway responses and operational headers are passed through as with `/fast`.

Set these environment variables through environment-specific Helm values:

```yaml
python:
  environment:
    SPEECH_AUDIO_STORAGE_ACCOUNT_URL: https://<account>.blob.core.windows.net
    SPEECH_AUDIO_STORAGE_CONTAINER: speech-audio
```

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
