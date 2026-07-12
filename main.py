import asyncio
import argparse
from analyzer.network import check_status
from analyzer.security import get_ip, certificate, get_geolocation
from analyzer.links import broken_links, get_links
from rich.console import Console
from rich.panel import Panel


async def analyze(Url):
    status = await check_status(Url)
    ip = get_ip(Url)
    geo = await get_geolocation(ip)
    cert = certificate(Url)
    links = await broken_links(Url)
    numberOfLinks = await get_links(Url)

    return {
        "status": status,
        "ip": ip,
        "geo": geo,
        "cert": cert,
        "links": links,
        "number of links": numberOfLinks
    }


def validate_url(urL):
    if not urL.startswith(("http://", "https://")):
        urL = "https://" + urL
    return urL

console = Console()

async def main(main_url):
    with console.status("[bold cyan]Analyzing website..."):
        report = await analyze(main_url)
    console.print(Panel(report["status"], title="Website Info", border_style="cyan"))
    console.print(Panel(f"IP: {report['ip']}\n{report['geo']}", title="IP & Location", border_style="yellow"))
    console.print(Panel(report["cert"], title="SSL Certificate", border_style="green"))
    console.print(Panel(report["links"], title="Links Checked", border_style="magenta"))
    console.print(Panel(report["number of links"], title="🔗 Count of links:", border_style="blue"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a website.")
    parser.add_argument("url", help="The URL to analyze.")
    args = parser.parse_args()
    url = validate_url(args.url)
    asyncio.run(main(url))
