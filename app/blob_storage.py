import logging
import os

from azure.storage.blob.aio import BlobClient, BlobServiceClient
from fastapi import HTTPException

from app import azure_auth

logger = logging.getLogger(__name__)

_client: BlobServiceClient | None = None


def get_blob_client(blob_name: str) -> BlobClient:
    global _client
    account_url = os.environ.get("SPEECH_AUDIO_STORAGE_ACCOUNT_URL")
    container = os.environ.get("SPEECH_AUDIO_STORAGE_CONTAINER")
    if not account_url:
        raise HTTPException(
            status_code=500, detail="SPEECH_AUDIO_STORAGE_ACCOUNT_URL is not configured"
        )
    if not container:
        raise HTTPException(
            status_code=500, detail="SPEECH_AUDIO_STORAGE_CONTAINER is not configured"
        )

    if _client is None:
        try:
            _client = BlobServiceClient(
                account_url=account_url,
                credential=azure_auth.get_credential(),
                max_single_get_size=4 * 1024 * 1024,
                max_chunk_get_size=4 * 1024 * 1024,
                max_single_put_size=4 * 1024 * 1024,
                max_block_size=4 * 1024 * 1024,
            )
        except ValueError:
            logger.exception("Failed to initialize audio blob storage client")
            raise HTTPException(
                status_code=500, detail="Could not initialize audio blob storage client"
            )
    return _client.get_blob_client(container=container, blob=blob_name)


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
