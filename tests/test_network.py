from core.network import check_status
import pytest
import asyncio
import aiohttp
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.mark.parametrize("exception_to_raise, expected_error", [
    (aiohttp.InvalidURL(url="hdfhdfhu"),"invalid_url"),
    (ValueError,"invalid_url"),

    (aiohttp.ClientConnectorError(connection_key=MagicMock, os_error=OSError()),"connection_failed"),

    (asyncio.TimeoutError,"timeout"),

    (aiohttp.ClientError,"client_error")
])
@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_get_exception_returns_error_for_check_status(mock_aiohttp_client_timeout,mock_aiohttp_client_session,exception_to_raise
                                                            ,expected_error):
    mock_timeout = MagicMock()
    mock_aiohttp_client_timeout.return_value = mock_timeout

    mock_session = MagicMock()
    mock_aiohttp_client_session.return_value.__aenter__.return_value = mock_session

    mock_response_context = AsyncMock()
    mock_session.get.return_value = mock_response_context
    mock_response_context.__aenter__.side_effect = exception_to_raise

    result = await check_status("https://www.google.com")
    assert result["error"] == expected_error
    assert result["status_code"] is None
    assert result["description"] is None
    assert result["title"] is None
    assert result["duration_ms"] is None

def make_mock_session(html_content, status=200):
    mock_session = MagicMock()
    mock_response_context = AsyncMock()
    mock_response_context.__aenter__.return_value = mock_response_context
    mock_response_context.status = status
    mock_response_context.text = AsyncMock(return_value=html_content)
    mock_session.get.return_value = mock_response_context
    return mock_session

@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_success_extracts_title_and_description(mock_client_timeout, mock_client_session):
    html = """
    <html>
        <head>
            <title>  My Page Title  </title>
            <meta name="description" content="My page description">
        </head>
        <body>Content</body>
    </html>
    """
    mock_session = make_mock_session(html, status=200)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    result = await check_status("https://www.google.com")

    assert result["error"] is None
    assert result["status_code"] == 200
    assert result["title"] == "My Page Title"
    assert result["description"] == "My page description"
    assert isinstance(result["duration_ms"], int)
    assert result["duration_ms"] >= 0


@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_no_title_tag_returns_none(mock_client_timeout, mock_client_session):
    html = "<html><head><meta name='description' content='Desc only'></head><body></body></html>"
    mock_session = make_mock_session(html, status=200)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    result = await check_status("https://www.google.com")

    assert result["title"] is None
    assert result["description"] == "Desc only"
    assert result["error"] is None


@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_no_meta_description_returns_none(mock_client_timeout, mock_client_session):
    html = "<html><head><title>Only Title</title></head><body></body></html>"
    mock_session = make_mock_session(html, status=200)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    result = await check_status("https://www.google.com")

    assert result["title"] == "Only Title"
    assert result["description"] is None
    assert result["error"] is None


@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_no_title_and_no_description(mock_client_timeout, mock_client_session):
    html = "<html><head></head><body>Nothing here</body></html>"
    mock_session = make_mock_session(html, status=200)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    result = await check_status("https://www.google.com")

    assert result["title"] is None
    assert result["description"] is None
    assert result["error"] is None
    assert result["status_code"] == 200


@pytest.mark.parametrize("status_code", [200, 301, 404, 500])
@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_returns_actual_status_code_regardless_of_value(
    mock_client_timeout, mock_client_session, status_code
):
    html = "<html><head><title>T</title></head></html>"
    mock_session = make_mock_session(html, status=status_code)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    result = await check_status("https://www.google.com")

    assert result["status_code"] == status_code
    assert result["error"] is None
    assert result["title"] == "T"


@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_strips_whitespace_from_title(mock_client_timeout, mock_client_session):
    html = "<html><head><title>\n   Spaced Title   \n</title></head></html>"
    mock_session = make_mock_session(html, status=200)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    result = await check_status("https://www.google.com")

    assert result["title"] == "Spaced Title"


@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_meta_description_with_empty_content(mock_client_timeout, mock_client_session):
    html = '<html><head><meta name="description" content=""></head></html>'
    mock_session = make_mock_session(html, status=200)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    result = await check_status("https://www.google.com")

    assert result["description"] == ""


@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_uses_10_second_timeout(mock_client_timeout, mock_client_session):
    html = "<html><head><title>T</title></head></html>"
    mock_session = make_mock_session(html, status=200)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    await check_status("https://www.google.com")

    mock_client_timeout.assert_called_once_with(total=10)


@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_passes_headers_to_session(mock_client_timeout, mock_client_session):
    from core.config import HEADERS

    html = "<html><head><title>T</title></head></html>"
    mock_session = make_mock_session(html, status=200)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    await check_status("https://www.google.com")

    _, kwargs = mock_client_session.call_args
    assert kwargs["headers"] == HEADERS


@patch("core.network.aiohttp.ClientSession")
@patch("core.network.aiohttp.ClientTimeout")
async def test_check_status_calls_get_with_correct_url(mock_client_timeout, mock_client_session):
    html = "<html><head><title>T</title></head></html>"
    mock_session = make_mock_session(html, status=200)
    mock_client_session.return_value.__aenter__.return_value = mock_session

    await check_status("https://www.example.com/page")

    mock_session.get.assert_called_once_with("https://www.example.com/page")
