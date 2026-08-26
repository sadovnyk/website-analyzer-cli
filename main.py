import asyncio
import argparse
from core.network import check_status
from core.security import get_ip, certificate, get_geolocation
from core.links import broken_links
from rich.console import Console
from rich.panel import Panel
from core.database import save_scan, save_links

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


def validate_url(urL):
    if not urL.startswith(("http://", "https://")):
        urL = "https://" + urL
    return urL


console = Console()


async def main(main_url):
    with console.status("[bold cyan]Analyzing website..."):
        report = await analyze(main_url)

    status = report["status"]
    if status["error"]:
        status_text = f"Error: {status['error']}"
    else:
        status_text = (
            f"Status code: {status['status_code']}\n"
            f"Title: {status['title']}\n"
            f"Description: {status['description']}\n"
            f"Duration: {status['duration_ms']} ms"
        )
    console.print(Panel(status_text, title="Website Info", border_style="cyan"))

    geo = report["geo"]
    if geo["error"]:
        geo_text = f"Error: {geo['error']}"
    else:
        geo_text = f"Country: {geo['country']}\nCity: {geo['city']}\nOrganization: {geo['org']}"
    console.print(Panel(f"IP: {report['ip']}\n{geo_text}", title="IP & Location", border_style="yellow"))

    cert = report["cert"]
    if cert["error"]:
        cert_text = f"Error: {cert['error']}"
    else:
        cert_text = f"Expires in {cert['ssl_days_left']} days"
    console.print(Panel(cert_text, title="SSL Certificate", border_style="green"))

    links = report["links"]
    if links["error"]:
        links_text = f"Unable to check links: {links['error']}"
    elif links["broken_links"]:
        links_text = "\n".join(f"{l['url']} -> {l['status'] or l['error']}" for l in links["broken_links"])
    else:
        links_text = "No broken links found"
    console.print(Panel(links_text, title="Links Checked", border_style="magenta"))

    console.print(Panel(str(links["total_links"]), title="Count of links", border_style="blue"))

    db_results = save_scan(main_url, report)

    if db_results["error"]:
        console.print(Panel(f"Data didn't save to MySQL!\nReason: {db_results['error']}", title="Error", border_style="red"))
    else:
        console.print(Panel("Data successfully saved to MySQL!", title="Good!", border_style="green"))
        mongo_results = save_links(db_results["scan_id"],links)
        if mongo_results["error"]:
            console.print(
                Panel(f"Data didn't save to MongoDB!\nReason: {mongo_results['error']}", title="Error", border_style="red"))
        else:
            console.print(Panel("Data successfully saved to MongoDB!", title="Good!", border_style="green"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a website.")
    parser.add_argument("url", help="The URL to analyze.")
    args = parser.parse_args()
    url = validate_url(args.url)

    try:
        asyncio.run(main(url))
    except KeyboardInterrupt:
        console.print("\n[bold red]Analysis interrupted by user.")
        raise SystemExit(1)