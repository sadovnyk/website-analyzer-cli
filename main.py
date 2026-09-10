import asyncio
from core.network import check_status
from core.security import get_ip, certificate, get_geolocation
from core.links import broken_links

async def analyze(Url):
    status = await check_status(Url)
    ip = get_ip(Url)
    geo = await get_geolocation(ip)
    cert = certificate(Url)
    links = await broken_links(Url)

    return {
        "status": status,
        "ip": ip,
        "geo": geo,
        "cert": cert,
        "links": links,
        "number_of_links": links["total_links"]
    }