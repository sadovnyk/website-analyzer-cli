import aiohttp
import asyncio
import time
from bs4 import BeautifulSoup
from analyzer.config import HEADERS

async def check_status(url):
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout,headers=HEADERS) as session:
            start = time.time()
            async with session.get(url) as response:
                end = time.time()
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                title = soup.title.text.strip() if soup.title else "Not found"
                meta_data = soup.find('meta', attrs={'name': 'description'})
                meta_description = meta_data['content'] if meta_data else "Not found"
                duration_ms = round((end - start) * 1000)
                report = (
                    f"URL: {url}\n"
                    f"Title: {title}\n"
                    f"Description: {meta_description}\n" 
                    f"Duration: {duration_ms}\n"
                )
                return report
    except aiohttp.ClientConnectorError:
        return f"Title: {url}"
    except asyncio.TimeoutError:
        return f"Timeout: {url}"

async def check_multiple(urls):
    tasks = [check_status(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    outputs = []
    for result in results:
        if isinstance(result, Exception):
            outputs.append(f"Error: {result}")
        else:
            outputs.append(result)
    return "\n".join(outputs)