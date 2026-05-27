from src.infrastructure.database.session import sessionmanager


async def test_sessionmanager_returns_sqlmodel_asyncsession_with_exec():
    async with sessionmanager.session() as session:
        assert hasattr(session, "exec")
        assert callable(session.exec)
