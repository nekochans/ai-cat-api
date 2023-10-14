import aiomysql
from usecase.db_handler_interface import DbHandlerInterface


class AiomysqlDbHandler(DbHandlerInterface):
    def __init__(self, connection: aiomysql.Connection) -> None:
        self.connection = connection

    async def begin(self) -> None:
        await self.connection.begin()

    async def commit(self) -> None:
        await self.connection.commit()

    async def rollback(self) -> None:
        await self.connection.rollback()

    def close(self) -> None:
        self.connection.close()
