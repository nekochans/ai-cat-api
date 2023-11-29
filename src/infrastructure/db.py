import os
import ssl
import asyncio
import aiomysql
from aiomysql import Connection

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.load_verify_locations(cafile=os.getenv("SSL_CERT_PATH"))


async def create_db_connection(db_name: str = "") -> Connection:
    loop = asyncio.get_event_loop()

    if os.getenv("IS_TESTING") == "1":
        use_db_name = db_name if db_name != "ai_cat_api_test" else os.getenv("DB_NAME")

        connection = await aiomysql.connect(
            host="ai-cat-api-mysql",
            port=3306,
            user="root",
            password=os.getenv("DB_PASSWORD"),
            db=use_db_name,
            loop=loop,
            cursorclass=aiomysql.DictCursor,
        )
        return connection

    connection = await aiomysql.connect(
        host=os.getenv("DB_HOST"),
        port=3306,
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        loop=loop,
        cursorclass=aiomysql.DictCursor,
        ssl=ctx,
    )

    return connection
