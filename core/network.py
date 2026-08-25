import aiohttp
import asyncio
import time
from bs4 import BeautifulSoup
from core.config import HEADERS


async def check_status(url):
    access = {
        "title": None,
        "description": None,
        "duration_ms": None,
        "status_code": None,
        "error": None
    }
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
            start = time.time()
            async with session.get(url) as response:
                end = time.time()
                html_content = await response.text(errors="ignore")
                soup = BeautifulSoup(html_content, 'html.parser')
                title = soup.title.text.strip() if soup.title else None
                meta_data = soup.find('meta', attrs={'name': 'description'})
                meta_description = meta_data['content'] if meta_data else None
                duration_ms = round((end - start) * 1000)
                access["title"] = title
                access["description"] = meta_description
                access["duration_ms"] = duration_ms
                access["status_code"] = response.status
                return access

    except (aiohttp.InvalidURL, ValueError):
        access["error"] = "invalid_url"
        return access
    except aiohttp.ClientConnectorError:
        access["error"] = "connection_failed"
        return access
    except (asyncio.TimeoutError, ValueError):
        access["error"] = "timeout"
        return access
    except aiohttp.ClientError as e:
        access["error"] = "client_error"
        return access