import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from analyzer.config import HEADERS

async def get_links(base_url):
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(base_url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                un_links = set()
                for tag in soup.find_all('a', href=True):
                    href = tag['href']
                    un_links.add(href)

                length = len(un_links)
                return f"{base_url} -> count of links: {length}"
    except aiohttp.ClientConnectorError:
        return f"{base_url} -> Connection error"
    except asyncio.TimeoutError:
        return f"{base_url} -> Timeout error"


async def extract_links(base_url):
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(base_url) as response:
                if response.status != 200:
                    return None, response.status
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                un_links = set()
                for tag in soup.find_all('a', href=True):
                    href = tag['href']
                    un_links.add(href)
                return un_links, 200
    except aiohttp.ClientConnectorError:
        return set()
    except asyncio.TimeoutError:
        return set()

async def get_many_links(urls):
    many_urls = [get_links(url) for url in urls]
    results = await asyncio.gather(*many_urls, return_exceptions=True)
    outputs = []
    for result in results:
        if isinstance(result, Exception):
            outputs.append(f"Error: {result}")
        else:
            outputs.append(result)
    return "\n".join(outputs)

async def check_link(session, url):
    try:
        async with session.head(url,timeout=aiohttp.ClientTimeout(total=3), allow_redirects=True) as response:
            return url, response.status
    except aiohttp.ClientConnectorError:
        return url, -1
    except asyncio.TimeoutError:
        return url, -2

async def check_links(urls):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        links = [check_link(session, link) for link in urls]
        results = await asyncio.gather(*links, return_exceptions=True)
        outputs = []
        for result in results:
            if isinstance(result, Exception):
                outputs.append(f"Error: {result}")
            else:
                url, status = result
                if status == -1:
                    outputs.append(f"Connection error: {url} status code: {status}")
                elif status == -2:
                    outputs.append(f"Timeout error: {url}, status code: {status}")
                else:
                    outputs.append(f"Link is working: {url}, status code: {status}")

        return "\n".join(outputs)

async def broken_links(url):
    un_links, status = await extract_links(url)

    if status != 200:
        return f"Unable to check links — the page returned status code {status}"

    absolute_links = [urljoin(url,link) for link in un_links]
    if not absolute_links:
        return "No absolute links found"
    return await check_links(absolute_links)