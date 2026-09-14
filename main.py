import asyncio
from core.network import check_status
from core.security import get_ip, certificate, get_geolocation
from core.links import broken_links


async def analyze(url):

    status_task = asyncio.create_task(check_status(url))
    ip_task = asyncio.create_task(asyncio.to_thread(get_ip, url))
    cert_task = asyncio.create_task(asyncio.to_thread(certificate, url))
    links_task = asyncio.create_task(broken_links(url))

    status, ip, cert, links = await asyncio.gather(
        status_task, ip_task, cert_task, links_task
    )

    geo = await get_geolocation(ip)

    return {
        "status": status,
        "ip": ip,
        "geo": geo,
        "cert": cert,
        "links": links,
        "number_of_links": links["total_links"]
    }