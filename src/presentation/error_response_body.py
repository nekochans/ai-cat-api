from pydantic import BaseModel
from typing import Literal


class UnauthorizedError(BaseModel):
    type: Literal["UNAUTHORIZED"]
    title: Literal["Invalid Authorization Header."]


class UnexpectedErrorBody(BaseModel):
    type: Literal["INTERNAL_SERVER_ERROR"]
    title: Literal["an unexpected error has occurred."]


class InvalidParam(BaseModel):
    name: str
    reason: str


class ValidationErrorBody(BaseModel):
    type: Literal["UNPROCESSABLE_ENTITY"]
    title: Literal["validation Error."]
    invalidParams: list[InvalidParam]
