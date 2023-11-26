import os
import ssl
import asyncio
import aiomysql
from aiomysql import Connection

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.load_verify_locations(cafile=os.getenv("SSL_CERT_PATH"))


async def create_db_connection() -> Connection:
    loop = asyncio.get_event_loop()

    if os.getenv("IS_TESTING") == "1":
        connection = await aiomysql.connect(
            host=os.getenv("DB_HOST"),
            port=3306,
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB_NAME"),
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
