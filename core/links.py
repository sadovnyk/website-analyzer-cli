import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from core.config import HEADERS


async def extract_links(base_url):
    access = {
        "links": None,
        "error": None,
        "status": None
    }
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(base_url) as response:
                if response.status != 200:
                    access["status"] = response.status
                    return access
                html = await response.text(errors="ignore")
                soup = BeautifulSoup(html, 'html.parser')
                un_links = set()
                for tag in soup.find_all('a', href=True):
                    href = str(tag['href']).strip()
                    un_links.add(href)
                access["links"] = un_links
                access["status"] = 200
                return access

    except (aiohttp.InvalidURL, ValueError):
        access["error"] = "invalid_url"
        return access
    except aiohttp.ClientConnectorError:
        access["error"] = "connection_failed"
        return access
    except asyncio.TimeoutError:
        access["error"] = "timeout"
        return access


async def check_link(session, url):
    access = {
        "url": url,
        "status": None,
        "error": None
    }
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=3), allow_redirects=True) as response:
            access["status"] = response.status
            return access
    except aiohttp.ClientConnectorError:
        access["error"] = "connection_failed"
        return access
    except asyncio.TimeoutError:
        access["error"] = "timeout"
        return access


async def check_links(urls):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        links = [check_link(session, link) for link in urls]
        results = await asyncio.gather(*links, return_exceptions=True)
        cleaned_results = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                result = {"url": url, "status": None, "error": str(result)}
            cleaned_results.append(result)

        return cleaned_results


async def broken_links(url):
    access = {
        "url": url,
        "broken_links": [],
        "error": None,
        "total_links": None
    }
    result = await extract_links(url)

    if result["error"] is not None:
        access["error"] = result["error"]
        return access

    if result["status"] != 200:
        access["error"] = f"Unable to check links — the page returned status code {result['status']}"
        return access

    absolute_links = [urljoin(url, link) for link in result["links"]]
    access["total_links"] = len(absolute_links)
    checked_links = await check_links(absolute_links)
    for link in checked_links:
        if link["error"] is not None or link["status"] is None or link["status"] >= 400:
            access["broken_links"].append(link)
    return access
