import socket
import ssl
import aiohttp
from urllib.parse import urlparse
from datetime import datetime, timezone
from analyzer.config import HEADERS

def get_ip(url):
        try:
            host = urlparse(url).hostname
            if not host:
                return "Not found IP"
            ip = socket.gethostbyname(host)
            return ip
        except (socket.gaierror,ValueError, UnicodeError):
            return "Not found IP"

async def get_geolocation(ip):
    if ip == "Not found IP":
        return "Not found geolocation"
    try:
        url = f"https://ipinfo.io/{ip}/json"
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as response:
                data = await response.json()
                results = (
                    f"Country: {data.get('country','Unknown')}\n"
                    f"City: {data.get('city','Unknown')}\n"
                    f"Org: {data.get('org','Unknown')}"
                )
                return results

    except (aiohttp.ClientError, ValueError):
        return "Not found geolocation"

def certificate(url):
    host = urlparse(url).hostname
    if not host:
        return "Invalid URL"
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as sSock:
                cert = sSock.getpeercert()
                if not cert:
                    return "Certificate not found"
                not_after = cert.get('notAfter')
                if not isinstance(not_after, str):
                    return "Certificate not found"
                date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                date = date.replace(tzinfo=timezone.utc)
                current_date = datetime.now(timezone.utc)
                expires = date - current_date
                return f"Certificate expires in {expires.days} days"
    except ssl.SSLError:
        return "SSL error"
    except (OSError, socket.timeout, UnicodeError):
        return "Connection error"
    except (KeyError, ValueError):
        return "Certificate not found"