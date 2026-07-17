from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import app.azure_auth as azure_auth


@pytest.fixture(autouse=True)
def reset_credential():
    """Ensure the module-level credential is reset between tests."""
    azure_auth._credential = None
    yield
    azure_auth._credential = None


def test_get_credential_creates_instance():
    with patch("app.azure_auth.WorkloadIdentityCredential") as mock_cls:
        mock_cls.return_value = MagicMock()
        cred = azure_auth._get_credential()
        assert cred is mock_cls.return_value
        mock_cls.assert_called_once()


def test_get_credential_reuses_instance():
    with patch("app.azure_auth.WorkloadIdentityCredential") as mock_cls:
        mock_cls.return_value = MagicMock()
        c1 = azure_auth._get_credential()
        c2 = azure_auth._get_credential()
        assert c1 is c2
        mock_cls.assert_called_once()


@pytest.mark.asyncio
async def test_get_token_returns_token_string():
    mock_cred = AsyncMock()
    mock_cred.get_token.return_value = MagicMock(token="my-token")
    with patch("app.azure_auth._get_credential", return_value=mock_cred):
        result = await azure_auth.get_token("api://scope/.default")
    assert result == "my-token"
    mock_cred.get_token.assert_called_once_with("api://scope/.default")


@pytest.mark.asyncio
async def test_close_credential_closes_and_resets():
    mock_cred = AsyncMock()
    azure_auth._credential = mock_cred
    await azure_auth.close_credential()
    mock_cred.close.assert_called_once()
    assert azure_auth._credential is None


@pytest.mark.asyncio
async def test_close_credential_noop_when_none():
    azure_auth._credential = None
    await azure_auth.close_credential()  # should not raise
