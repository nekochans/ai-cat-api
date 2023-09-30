import os
from secrets import compare_digest
from fastapi import status, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

BASIC_AUTH_USERNAME = os.environ.get("BASIC_AUTH_USERNAME")
BASIC_AUTH_PASSWORD = os.environ.get("BASIC_AUTH_PASSWORD")


def basic_auth(
    credentials: HTTPBasicCredentials = Depends(security),
) -> HTTPBasicCredentials:
    correct_username = compare_digest(credentials.username, BASIC_AUTH_USERNAME or "")
    correct_password = compare_digest(credentials.password, BASIC_AUTH_PASSWORD or "")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"type": "UNAUTHORIZED", "title": "Invalid Authorization Header."},
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials
