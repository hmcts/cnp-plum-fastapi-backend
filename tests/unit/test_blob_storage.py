from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app import blob_storage


@pytest.fixture(autouse=True)
def storage_env(monkeypatch):
    monkeypatch.setenv("SPEECH_AUDIO_STORAGE_ACCOUNT_URL", "https://audio.blob.core.windows.net")
    monkeypatch.setenv("SPEECH_AUDIO_STORAGE_CONTAINER", "speech-audio")
    blob_storage._client = None
    yield
    blob_storage._client = None


def test_storage_client_reuses_workload_credential_and_connection():
    with patch("app.blob_storage.BlobServiceClient") as client_class, patch(
        "app.azure_auth.get_credential"
    ) as get_credential:
        first = blob_storage.get_blob_client("first")
        second = blob_storage.get_blob_client("second")

    client_class.assert_called_once()
    assert client_class.call_args.kwargs["credential"] is get_credential.return_value
    assert client_class.call_args.kwargs["account_url"] == "https://audio.blob.core.windows.net"
    get_credential.assert_called_once()
    assert first is second
    assert client_class.return_value.get_blob_client.call_args_list[0].kwargs == {
        "container": "speech-audio", "blob": "first"
    }
    assert client_class.return_value.get_blob_client.call_args_list[1].kwargs == {
        "container": "speech-audio", "blob": "second"
    }


@pytest.mark.parametrize(
    "variable", ["SPEECH_AUDIO_STORAGE_ACCOUNT_URL", "SPEECH_AUDIO_STORAGE_CONTAINER"]
)
def test_storage_requires_configuration(variable, monkeypatch):
    monkeypatch.delenv(variable)
    with pytest.raises(HTTPException) as error:
        blob_storage.get_blob_client("audio")
    assert error.value.status_code == 500
    assert variable in error.value.detail


async def test_storage_client_closes_and_resets_without_closing_shared_credential():
    client = AsyncMock()
    blob_storage._client = client
    with patch("app.azure_auth.close_credential", AsyncMock()) as close_credential:
        await blob_storage.close_client()
        await blob_storage.close_client()
    client.close.assert_awaited_once()
    close_credential.assert_not_awaited()
    assert blob_storage._client is None


def test_storage_reports_invalid_workload_identity_configuration():
    with patch(
        "app.azure_auth.get_credential", side_effect=ValueError("Missing tenant ID")
    ), pytest.raises(HTTPException) as error:
        blob_storage.get_blob_client("audio")
    assert error.value.status_code == 500
    assert error.value.detail == "Could not initialize audio blob storage client"
    assert blob_storage._client is None
