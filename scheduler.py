import asyncio

from datetime import datetime

from core.database import get_active_sites, save_scan, save_links
from main import analyze


async def run_schedule():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launching the scheduler...")
    active_sites = get_active_sites()

    if active_sites["success"] is True:
        if not active_sites["result"]:
            print("There are no active sites to scan.")
        for site in active_sites["result"]:
            print(f"Website scan: {site['url']}")

            scan_data = await analyze(site["url"])

            save_result = save_scan(site["url"], scan_data, site["id"])

            if save_result["success"] is True:
                save_links(save_result["scan_id"], scan_data["links"])
                print(f"The data has been successfully saved for {site['url']}")
            else:
                print(f"Error (MySQL): {save_result['error']}")
    else:
        print(f"Database error: {active_sites['error']}")


if __name__ == "__main__":
    asyncio.run(run_schedule())