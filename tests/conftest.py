import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import logging
import aiohttp
@pytest.fixture
def mock_aiohttp_get():
    with patch("core.links.aiohttp.ClientSession") as mock_session_class:

        mock_session = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        mock_response_context = AsyncMock()
        mock_response_context.__aenter__.return_value = mock_response_context

        mock_session.get.return_value = mock_response_context

        yield mock_response_context

@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture
def logger_module(tmp_path, monkeypatch):
    import core.logger as logger_module

    fake_log_file = tmp_path / "cron.log"
    monkeypatch.setattr(logger_module, "LOG_DIR", str(tmp_path))
    monkeypatch.setattr(logger_module, "LOG_FILE", str(fake_log_file))

    yield logger_module

    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith("test_logger"):
            lg = logging.getLogger(name)
            for h in lg.handlers[:]:
                h.close()
                lg.removeHandler(h)

@pytest.fixture
def mock_cursor():
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    return cursor

@pytest.fixture
def mock_connection(mock_cursor):
    conn = MagicMock()
    conn.cursor.return_value = mock_cursor
    return conn

@pytest.fixture
def mock_mongo_collection():
    collection = MagicMock()
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.__getitem__.return_value.__getitem__.return_value = collection
    return client, collection