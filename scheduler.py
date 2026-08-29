import asyncio
from core.scan_runner import scan_one_site
from datetime import datetime
from core.database import get_sites


async def run_schedule():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launching the scheduler...")
    active_sites = get_sites(only_active=True)

    if active_sites["success"] is True:
        if not active_sites["result"]:
            print("There are no active sites to scan.")
        for site in active_sites["result"]:
            print(f"Website scan: {site['url']}")
            await scan_one_site(site["url"], site["id"])

    else:
        print(f"Database error: {active_sites['error']}")


if __name__ == "__main__":
    asyncio.run(run_schedule())