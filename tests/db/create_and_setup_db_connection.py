import os
import asyncio
import aiomysql
from aiomysql import Connection
from typing import Tuple
from tests.db.setup_test_database import setup_test_database, create_test_db_name


async def create_and_setup_db_connection() -> Tuple[Connection, str]:
    loop = asyncio.get_event_loop()

    host = "ai-cat-api-mysql"
    port = 3306
    user = "root"
    password = os.getenv("DB_PASSWORD")

    connection = await aiomysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        db="ai_cat_api_test",
        loop=loop,
        cursorclass=aiomysql.DictCursor,
    )

    test_db_name = create_test_db_name()

    await setup_test_database(
        connection,
        test_db_name,
    )

    connection = await aiomysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        db=test_db_name,
        loop=loop,
        cursorclass=aiomysql.DictCursor,
    )

    return connection, test_db_name
