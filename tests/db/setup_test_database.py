import os
import requests
import uuid
from typing import TypedDict, List
from aiomysql import Connection
from functools import lru_cache


class TableSchema(TypedDict):
    name: str
    html: str
    raw: str
    annotated: bool


class BranchSchemas(TypedDict):
    data: List[TableSchema]


@lru_cache()
def fetch_db_branch_schemas() -> BranchSchemas:
    org = os.getenv("PLANET_SCALE_ORG")
    db = os.getenv("PLANET_SCALE_TEST_DB_NAME")
    branch = os.getenv("PLANET_SCALE_TEST_DB_BRANCH")

    service_token_id = os.getenv("PLANET_SCALE_SERVICE_TOKEN_ID")
    service_token_secret = os.getenv("PLANET_SCALE_SERVICE_TOKEN_SECRET")

    credential = f"{service_token_id}:{service_token_secret}"

    url = f"https://api.planetscale.com/v1/organizations/{org}/databases/{db}/branches/{branch}/schema"
    headers = {"Authorization": credential, "Accept": "application/json"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


async def setup_test_database(connection: Connection, db_name: str) -> None:
    branch_schemas = fetch_db_branch_schemas()

    async with connection.cursor() as cursor:
        await cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        await cursor.execute(f"CREATE DATABASE {db_name}")
        await cursor.execute(f"USE {db_name}")

        for table in branch_schemas["data"]:
            create_table_sql = table["raw"].replace("\n", " ").replace("\t", " ")
            await cursor.execute(create_table_sql)


def create_test_db_name() -> str:
    return f"test_db_{uuid.uuid4().hex[:8]}"
