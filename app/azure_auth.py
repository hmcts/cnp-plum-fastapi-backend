from azure.identity.aio import WorkloadIdentityCredential

_credential: WorkloadIdentityCredential | None = None


def _get_credential() -> WorkloadIdentityCredential:
    global _credential
    if _credential is None:
        # Uses AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_FEDERATED_TOKEN_FILE,
        # injected into the pod by the AKS workload-identity webhook.
        _credential = WorkloadIdentityCredential()
    return _credential


async def get_token(scope: str) -> str:
    token = await _get_credential().get_token(scope)
    return token.token


async def close_credential() -> None:
    global _credential
    if _credential is not None:
        await _credential.close()
        _credential = None
