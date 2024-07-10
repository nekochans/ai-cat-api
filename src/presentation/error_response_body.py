from pydantic import BaseModel, Field
from typing import Literal


class UnauthorizedError(BaseModel):
    type: Literal["UNAUTHORIZED"] = Field(
        description="問題のタイプを識別する文字列 RFC7807を参考に定義した https://zenn.dev/ryamakuchi/articles/d7c932afc57e30",
        json_schema_extra={
            "examples": ["UNAUTHORIZED"],
        },
    )
    title: Literal["Invalid Authorization Header."] = Field(
        description="エラーのタイトル RFC7807を参考に定義した https://zenn.dev/ryamakuchi/articles/d7c932afc57e30",
        json_schema_extra={
            "examples": ["Invalid Authorization Header."],
        },
    )


class UnexpectedErrorBody(BaseModel):
    type: Literal["INTERNAL_SERVER_ERROR"] = Field(
        description="問題のタイプを識別する文字列 RFC7807を参考に定義した https://zenn.dev/ryamakuchi/articles/d7c932afc57e30",
        json_schema_extra={
            "examples": ["INTERNAL_SERVER_ERROR"],
        },
    )
    title: Literal["an unexpected error has occurred."] = Field(
        description="エラーのタイトル RFC7807を参考に定義した https://zenn.dev/ryamakuchi/articles/d7c932afc57e30",
        json_schema_extra={
            "examples": ["an unexpected error has occurred."],
        },
    )


class InvalidParam(BaseModel):
    name: str = Field(
        description="バリデーションに引っかかったキー名 RFC7807を参考に定義した https://zenn.dev/ryamakuchi/articles/d7c932afc57e30",
        json_schema_extra={
            "examples": ["userId", "message"],
        },
    )
    reason: str = Field(
        description="バリデーションに引っかかった理由 RFC7807を参考に定義した https://zenn.dev/ryamakuchi/articles/d7c932afc57e30",
        json_schema_extra={
            "examples": [
                "userId is not in UUID format",
                "message must be at least 2 character and no more than 5,000 characters",
            ],
        },
    )


class ValidationErrorBody(BaseModel):
    type: Literal["UNPROCESSABLE_ENTITY"] = Field(
        description="問題のタイプを識別する文字列 RFC7807を参考に定義した https://zenn.dev/ryamakuchi/articles/d7c932afc57e30",
        json_schema_extra={
            "examples": ["UNPROCESSABLE_ENTITY"],
        },
    )
    title: Literal["validation Error."] = Field(
        description="エラーのタイトル RFC7807を参考に定義した https://zenn.dev/ryamakuchi/articles/d7c932afc57e30",
        json_schema_extra={
            "examples": ["validation Error."],
        },
    )
    invalidParams: list[InvalidParam] = Field(
        description="バリデーションエラーの詳細情報 RFC7807を参考に定義した https://zenn.dev/ryamakuchi/articles/d7c932afc57e30",
        json_schema_extra={
            "examples": [
                {
                    "name": "userId",
                    "reason": "userId is not in UUID format",
                },
                {
                    "name": "message",
                    "reason": "message must be at least 2 character and no more than 5,000 characters",
                },
            ],
        },
    )
