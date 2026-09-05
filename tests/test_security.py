from core.security import get_ip, get_geolocation, certificate
from aioresponses import aioresponses
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import socket
import aiohttp
import ssl
from datetime import datetime, timezone

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

@patch("core.security.socket.gethostbyname")
def test_get_ip_success_returns_resolved_ip(mock_gethostbyname):
    mock_gethostbyname.return_value = "142.250.74.68"

    result = get_ip("https://www.google.com")

    assert result == "142.250.74.68"
    mock_gethostbyname.assert_called_once_with("www.google.com")

class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2024, 1, 1, tzinfo=timezone.utc)


@patch("core.security.datetime", FrozenDateTime)
@patch("core.security.ssl.create_default_context")
@patch("core.security.socket.create_connection")
def test_certificate_calculates_exact_days_left(mock_create_connection, mock_create_default_context):
    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context
    mock_socket = MagicMock()
    mock_create_connection.return_value.__enter__.return_value = mock_socket

    mock_ssl_sock = MagicMock()
    mock_context.wrap_socket.return_value.__enter__.return_value = mock_ssl_sock
    mock_ssl_sock.getpeercert.return_value = {"notAfter": "Jan 11 00:00:00 2024 GMT"}

    result = certificate("https://www.google.com")

    assert result["error"] is None
    assert result["valid"] is True
    assert result["ssl_days_left"] == 10


@patch("core.security.datetime", FrozenDateTime)
@patch("core.security.ssl.create_default_context")
@patch("core.security.socket.create_connection")
def test_certificate_expired_yesterday_is_invalid_with_negative_days(mock_create_connection, mock_create_default_context):
    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context
    mock_socket = MagicMock()
    mock_create_connection.return_value.__enter__.return_value = mock_socket

    mock_ssl_sock = MagicMock()
    mock_context.wrap_socket.return_value.__enter__.return_value = mock_ssl_sock
    mock_ssl_sock.getpeercert.return_value = {"notAfter": "Dec 31 00:00:00 2023 GMT"}

    result = certificate("https://www.google.com")

    assert result["error"] is None
    assert result["valid"] is False
    assert result["ssl_days_left"] < 0


@patch("core.security.ssl.create_default_context")
@patch("core.security.socket.create_connection")
def test_certificate_calls_wrap_socket_with_correct_hostname(mock_create_connection, mock_create_default_context):
    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context
    mock_socket = MagicMock()
    mock_create_connection.return_value.__enter__.return_value = mock_socket

    mock_ssl_sock = MagicMock()
    mock_context.wrap_socket.return_value.__enter__.return_value = mock_ssl_sock
    mock_ssl_sock.getpeercert.return_value = {"notAfter": "Sep 10 12:00:00 2030 GMT"}

    certificate("https://www.google.com")

    mock_create_connection.assert_called_once_with(("www.google.com", 443))
    mock_context.wrap_socket.assert_called_once_with(mock_socket, server_hostname="www.google.com")

async def test_get_geolocation_success_returns_country_city_org():
    with aioresponses() as mock:
        mock.get(
            "https://ipinfo.io/8.8.8.8/json",
            status=200,
            payload={"country": "US", "city": "Mountain View", "org": "Google LLC"},
        )
        result = await get_geolocation("8.8.8.8")

    assert result["error"] is None
    assert result["country"] == "US"
    assert result["city"] == "Mountain View"
    assert result["org"] == "Google LLC"


async def test_get_geolocation_missing_fields_default_to_none():
    with aioresponses() as mock:
        mock.get(
            "https://ipinfo.io/8.8.8.8/json",
            status=200,
            payload={"country": "US"},
        )
        result = await get_geolocation("8.8.8.8")

    assert result["error"] is None
    assert result["country"] == "US"
    assert result["city"] is None
    assert result["org"] is None


async def test_get_geolocation_empty_response_returns_all_none():
    with aioresponses() as mock:
        mock.get("https://ipinfo.io/8.8.8.8/json", status=200, payload={})
        result = await get_geolocation("8.8.8.8")

    assert result["error"] is None
    assert result["country"] is None
    assert result["city"] is None
    assert result["org"] is None


async def test_get_geolocation_uses_correct_url_for_given_ip():
    with aioresponses() as mock:
        mock.get("https://ipinfo.io/1.1.1.1/json", status=200, payload={"country": "AU"})
        result = await get_geolocation("1.1.1.1")

    assert result["country"] == "AU"