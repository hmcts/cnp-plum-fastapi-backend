import os

from fastapi import HTTPException


def gateway_scope() -> str:
    scope = os.environ.get("AI_GATEWAY_SCOPE")
    if not scope:
        raise HTTPException(status_code=500, detail="AI_GATEWAY_SCOPE is not configured")
    return scope


def subscription_key(file_environment_variable: str, environment_variable: str, error_message: str) -> str:
    key_file = os.environ.get(file_environment_variable)
    if key_file:
        with open(key_file) as file:
            return file.read().strip()

    key = os.environ.get(environment_variable)
    if not key:
        raise HTTPException(status_code=500, detail=error_message)
    return key