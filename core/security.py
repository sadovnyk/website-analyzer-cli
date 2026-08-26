import socket
import ssl
import aiohttp
from urllib.parse import urlparse
from datetime import datetime, timezone
from core.config import HEADERS


def get_ip(url):
    try:
        host = urlparse(url).hostname
        if not host:
            return None
        ip = socket.gethostbyname(host)
        return ip
    except (socket.gaierror, ValueError, UnicodeError):
        return None


async def get_geolocation(ip):
    access = {
        "country": None,
        "city": None,
        "org": None,
        "error": None
    }

    if ip is None:
        access["error"] = "invalid_ip"
        return access

    try:
        url = f"https://ipinfo.io/{ip}/json"
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as response:
                data = await response.json()
                access["country"] = data.get("country", None)
                access["city"] = data.get("city", None)
                access["org"] = data.get("org", None)
                return access

    except (aiohttp.ClientError, ValueError):
        access["error"] = "failed_to_fetch_geolocation"
        return access


def certificate(url):
    access = {
        "ssl_days_left": None,
        "error": None,
        "valid": None
    }
    host = urlparse(url).hostname
    if not host:
        access["error"] = "invalid_url"
        return access
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as sSock:
                cert = sSock.getpeercert()
                if not cert:
                    access["error"] = "certificate_not_found"
                    return access
                not_after = cert.get('notAfter')
                if not isinstance(not_after, str):
                    access["error"] = "certificate_not_found"
                    return access
                date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                date = date.replace(tzinfo=timezone.utc)
                current_date = datetime.now(timezone.utc)
                expires = date - current_date
                access["ssl_days_left"] = expires.days
                if expires.days < 0:
                    access["valid"] = False
                else:
                    access["valid"] = True
                return access
    except ssl.SSLError:
        access["error"] = "ssl_error"
        return access
    except (OSError, socket.timeout, UnicodeError):
        access["error"] = "connection_error"
        return access
    except (KeyError, ValueError):
        access["error"] = "certificate_not_found"
        return access