from typing import Protocol


class DbHandlerInterface(Protocol):
    async def begin(self) -> None:
        ...

    async def commit(self) -> None:
        ...

    async def rollback(self) -> None:
        ...

    def close(self) -> None:
        ...
