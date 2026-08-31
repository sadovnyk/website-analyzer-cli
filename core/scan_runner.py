from core.database import save_scan, save_links
from core.logger import get_logger
from main import analyze

logger = get_logger(__name__)

async def scan_one_site(url, site_id):
    scan_data = await analyze(url)
    save_result = save_scan(url, scan_data, site_id)

    if save_result["success"] is True:
        save_links(save_result["scan_id"], scan_data["links"])
    else:
        logger.error(f"Error (MySQL): {save_result['error']}")
