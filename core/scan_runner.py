import asyncio
from core.database import save_scan, save_links
from core.logger import get_logger
from core.security import is_safe_host
from main import analyze

logger = get_logger(__name__)

async def scan_one_site(url, site_id):

    if not await asyncio.to_thread(is_safe_host, url):
        logger.warning(f"Blocked scan of unsafe/private host: {url}")
        return

    scan_data = await analyze(url)
    save_result = save_scan(url, scan_data, site_id)

    if save_result["success"] is True:
        links_result = save_links(save_result["scan_id"], scan_data["links"])
        if links_result["success"] is not True:
            logger.error(f"Error (Mongo): {links_result['error']}")
    else:
        logger.error(f"Error (MySQL): {save_result['error']}")