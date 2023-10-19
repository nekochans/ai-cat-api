from usecase.db_handler_interface import DbHandlerInterface


class MockDbHandler(DbHandlerInterface):
    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass
