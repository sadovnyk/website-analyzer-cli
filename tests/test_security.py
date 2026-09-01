from core.security import get_ip, get_geolocation, certificate
from aioresponses import aioresponses
def test_get_ip_returns_none_for_invalid_url():
    assert get_ip(" fghfugh ") is None

def test_get_certificate_returns_none_for_invalid_url():
    result = certificate("not a url")
    assert result["error"] == "invalid_url"

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

