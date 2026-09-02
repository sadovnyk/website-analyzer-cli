from core.security import get_ip, get_geolocation, certificate
from aioresponses import aioresponses
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import socket
import aiohttp
import ssl

def test_get_ip_returns_none_for_invalid_url():
    assert get_ip(" fghfugh ") is None

def test_get_certificate_returns_none_for_invalid_url():
    result = certificate("not a url")
    assert result["error"] == "invalid_url"

@patch("core.security.ssl.create_default_context")
@patch("core.security.socket.create_connection")
def test_get_certificate_returns_cert_not_found_for_invalid_url(mock_create_connection,
                                                                mock_create_default_context):

    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context

    mock_socket = MagicMock()
    mock_create_connection.return_value.__enter__.return_value = mock_socket

    mock_ssl_sock = MagicMock()
    mock_socket.wrap_socket.return_value.__enter__.return_value = mock_ssl_sock

    mock_ssl_sock.getpeercert.return_value = None

    result = certificate("https://www.google.com")

    assert result["error"] == "certificate_not_found"
    assert result["valid"] is None
    assert result["ssl_days_left"] is None


@patch("core.security.ssl.create_default_context")
@patch("core.security.socket.create_connection")
def test_get_certificate_returns_cert_not_found_for_notAfter_not_a_string(mock_create_connection,
                                                                         mock_create_default_context):
    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context

    mock_socket = MagicMock()
    mock_create_connection.return_value.__enter__.return_value = mock_socket

    mock_ssl_sock =  MagicMock()
    mock_socket.wrap_socket.return_value.__enter__.return_value = mock_ssl_sock

    mock_ssl_sock.getpeercert.return_value = {"notAfter": 1234567890}

    result = certificate("https://www.google.com")

    assert result["error"] == "certificate_not_found"
    assert result["valid"] is None
    assert result["ssl_days_left"] is None


@pytest.mark.parametrize("cert_date ,expected_valid", [
    ("Sep 10 12:00:00 2030 GMT", True),
    ("Sep 10 12:00:00 2021 GMT", False),
])
@patch("core.security.ssl.create_default_context")
@patch("core.security.socket.create_connection")
def test_certificate_validity_dates(mock_create_connection,mock_create_default_context,cert_date,expected_valid):
    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context
    mock_socket = MagicMock()
    mock_create_connection.return_value.__enter__.return_value = mock_socket

    mock_ssl_sock =  MagicMock()
    mock_context.wrap_socket.return_value.__enter__.return_value = mock_ssl_sock

    mock_ssl_sock.getpeercert.return_value = {"notAfter": cert_date}

    result = certificate("https://www.google.com")
    assert result["valid"] is expected_valid


@pytest.mark.parametrize("exception_to_raise", [
    ValueError,
    UnicodeError,
    socket.gaierror
])
@patch("core.security.socket.gethostbyname")
def test_get_exception_returns_error_for_get_ip(mock_gethostbyname,exception_to_raise):
    mock_gethostbyname.side_effect = exception_to_raise
    result = get_ip("https://www.google.com")
    assert result is None


@pytest.mark.parametrize("exception_to_raise", [
    aiohttp.ClientError,
    ValueError
])
@patch("core.security.aiohttp.ClientSession")
async def test_get_exception_returns_error_for_get_geolocation(mock_aiohttp_client_session,exception_to_raise):
    mock_connection = MagicMock()
    mock_aiohttp_client_session.return_value.__aenter__.return_value = mock_connection

    mock_response_context = AsyncMock()

    mock_connection.get.return_value = mock_response_context
    mock_response_context.__aenter__.side_effect = exception_to_raise

    result = await get_geolocation("https://www.google.com")
    assert result["error"] == "failed_to_fetch_geolocation"


@pytest.mark.parametrize("exception_to_raise, expected_error", [
    (ssl.SSLError, "ssl_error"),
    (OSError,"connection_error"),
    (socket.timeout,"connection_error"),
    (UnicodeError,"connection_error"),
    (KeyError,"certificate_not_found"),
    (ValueError,"certificate_not_found")
])
@patch("core.security.ssl.create_default_context")
@patch("core.security.socket.create_connection")
def test_get_certificate_returns_ssl_error(mock_create_connection,mock_create_default_context,
                                           exception_to_raise,expected_error):
    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context
    mock_socket = MagicMock()
    mock_create_connection.return_value.__enter__.return_value = mock_socket

    mock_ssl_sock = MagicMock()
    mock_context.wrap_socket.return_value.__enter__.return_value = mock_ssl_sock

    mock_ssl_sock.getpeercert.side_effect = exception_to_raise

    result = certificate("https://www.google.com")
    assert result["error"] == expected_error
    assert result["valid"] is None
    assert result["ssl_days_left"] is None

async def test_get_geolocation_returns_error_on_api_failure():
    with aioresponses() as mock:
        mock.get("https://ipinfo.io/8.8.8.8/json", status=404,body="Not Found")
        result = await get_geolocation("8.8.8.8")

    assert result["error"] == "failed_to_fetch_geolocation"
    assert result["country"] is None
    assert result["city"] is None
    assert result["org"] is None

async def test_get_geolocation_returns_error_for_none_ip():
    result = await get_geolocation(None)
    assert result["error"] == "invalid_ip"

