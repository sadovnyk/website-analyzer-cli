import socket
import ssl
import aiohttp
from urllib.parse import urlparse
from datetime import datetime, timezone
from analyzer.config import HEADERS

def get_ip(url):
        try:
            host = urlparse(url).hostname
            ip = socket.gethostbyname(host)
            return ip
        except (socket.gaierror,ValueError):
            return "Not found IP"

async def get_geolocation(ip):
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
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as sSock:
                cert = sSock.getpeercert()
                date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                date = date.replace(tzinfo=timezone.utc)
                current_date = datetime.now(timezone.utc)
                expires = date - current_date
                return f"Certificate expires in {expires.days} days"
    except ssl.SSLError:
        return "SSL error"
    except (OSError, socket.timeout):
        return "Connection error"
    except KeyError:
        return "Certificate not found"