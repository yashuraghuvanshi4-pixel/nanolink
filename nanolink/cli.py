"""Command-line interface for nanolink URL shortener and analytics engine."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from nanolink import __version__
from nanolink.config import Settings
from nanolink.core.analytics import AnalyticsEngine
from nanolink.core.qr import QRCode
from nanolink.core.service import (
    LinkService,
    InvalidURLError,
    InvalidAliasError,
    AliasAlreadyExistsError,
    LinkNotFoundError,
    LinkExpiredError,
)
from nanolink.storage.db import Database, DEFAULT_DB_PATH

# Terminal color styling
USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def color(text: str, code: str) -> str:
    """Format text with ANSI escape codes if color is enabled."""
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(text: str) -> str:
    return color(text, "1")


def green(text: str) -> str:
    return color(text, "32")


def cyan(text: str) -> str:
    return color(text, "36")


def yellow(text: str) -> str:
    return color(text, "33")


def red(text: str) -> str:
    return color(text, "31")


def dim(text: str) -> str:
    return color(text, "2")


def render_bar(count: int, max_count: int, width: int = 24) -> str:
    """Render a text-based horizontal bar for metrics."""
    if max_count <= 0:
        return ""
    filled = int((count / max_count) * width)
    return "█" * max(1, filled) if count > 0 else ""


def build_parser() -> argparse.ArgumentParser:
    """Construct argument parser for CLI commands."""
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(
        prog="nanolink",
        description="⚡ High-performance URL shortener & analytics engine",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=settings.db_path,
        help=f"Path to SQLite database file (default: {settings.db_path})",
    )
    parser.add_argument(
        "--version", action="version", version=f"nanolink v{__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. shorten
    p_shorten = subparsers.add_parser("shorten", help="Shorten a long URL")
    p_shorten.add_argument("url", type=str, help="Destination URL (http/https)")
    p_shorten.add_argument("-a", "--alias", type=str, help="Custom short alias")
    p_shorten.add_argument("-t", "--title", type=str, help="Optional link title")
    p_shorten.add_argument("--ttl", type=int, help="Time to live in seconds")
    p_shorten.add_argument("--max-clicks", type=int, help="Maximum allowed clicks")
    p_shorten.add_argument(
        "--base-url", type=str, default=settings.base_url, help=f"Base redirect URL (default: {settings.base_url})"
    )
    p_shorten.add_argument("--qr", action="store_true", help="Print QR code in terminal")
    p_shorten.add_argument("--json", action="store_true", help="Output as JSON")

    # 2. resolve
    p_resolve = subparsers.add_parser("resolve", help="Look up target URL by short code")
    p_resolve.add_argument("code", type=str, help="Short link code")
    p_resolve.add_argument("--json", action="store_true", help="Output as JSON")

    # 3. stats
    p_stats = subparsers.add_parser("stats", help="View click analytics for a short link")
    p_stats.add_argument("code", type=str, help="Short link code")
    p_stats.add_argument("--json", action="store_true", help="Output as JSON")

    # 4. list
    p_list = subparsers.add_parser("list", help="List shortened links")
    p_list.add_argument("-n", "--limit", type=int, default=20, help="Max links to show")
    p_list.add_argument("--offset", type=int, default=0, help="Pagination offset")
    p_list.add_argument("--json", action="store_true", help="Output as JSON")

    # 5. qr
    p_qr = subparsers.add_parser("qr", help="Generate QR code for a short link")
    p_qr.add_argument("code", type=str, help="Short link code")
    p_qr.add_argument(
        "--base-url", type=str, default="http://localhost:8000", help="Base redirect URL"
    )
    p_qr.add_argument("--ascii", action="store_true", help="Render using plain ASCII")
    p_qr.add_argument("--svg", type=str, help="Save QR code to SVG file path")

    # 6. delete
    p_delete = subparsers.add_parser("delete", help="Delete a short link")
    p_delete.add_argument("code", type=str, help="Short link code")
    p_delete.add_argument("-f", "--force", action="store_true", help="Skip prompt")
    p_delete.add_argument("--json", action="store_true", help="Output as JSON")

    # 7. bulk
    p_bulk = subparsers.add_parser("bulk", help="Shorten multiple URLs from a file")
    p_bulk.add_argument("file", type=str, help="Path to JSON or text file (one URL per line)")
    p_bulk.add_argument("--base-url", type=str, default="http://localhost:8000", help="Base redirect URL")
    p_bulk.add_argument("--json", action="store_true", help="Output as JSON")

    # 8. export
    p_export = subparsers.add_parser("export", help="Export click telemetry to CSV or JSON")
    p_export.add_argument("code", type=str, help="Short link code")
    p_export.add_argument("--format", choices=["csv", "json"], default="csv", help="Export format")
    p_export.add_argument("-o", "--output", type=str, help="Save to output file path")

    # 9. search
    p_search = subparsers.add_parser("search", help="Search links by query")
    p_search.add_argument("query", type=str, help="Search string across code, URL, title, tags")
    p_search.add_argument("-n", "--limit", type=int, default=20, help="Max results")
    p_search.add_argument("--json", action="store_true", help="Output as JSON")

    # 10. serve
    p_serve = subparsers.add_parser("serve", help="Launch redirect engine & REST API server")
    p_serve.add_argument("-p", "--port", type=int, default=settings.port, help=f"Server port (default: {settings.port})")
    p_serve.add_argument("-H", "--host", type=str, default=settings.host, help=f"Host interface (default: {settings.host})")

    # 11. backup
    p_backup = subparsers.add_parser("backup", help="Create a hot backup of the SQLite database")
    p_backup.add_argument("target", type=str, help="Destination file path for backup")

    # 12. vacuum
    p_vacuum = subparsers.add_parser("vacuum", help="Compact and optimize SQLite storage")

    return parser


def cmd_shorten(args: argparse.Namespace, service: LinkService) -> int:
    try:
        link = service.shorten(
            url=args.url,
            custom_alias=args.alias,
            title=args.title,
            ttl_seconds=args.ttl,
            max_clicks=args.max_clicks,
        )
    except (InvalidURLError, InvalidAliasError, AliasAlreadyExistsError) as err:
        if args.json:
            print(json.dumps({"error": str(err)}))
        else:
            print(red(f"Error: {err}"), file=sys.stderr)
        return 1

    short_url = f"{args.base_url.rstrip('/')}/{link.code}"

    if args.json:
        data = link.to_dict()
        data["short_url"] = short_url
        print(json.dumps(data, indent=2))
        return 0

    print(bold(green("\n✔ URL successfully shortened!")))
    print(f"  {bold('Short URL:')}    {cyan(short_url)}")
    print(f"  {bold('Target URL:')}   {link.target_url}")
    print(f"  {bold('Code:')}         {link.code}")
    if link.title:
        print(f"  {bold('Title:')}        {link.title}")
    if link.expires_at:
        print(f"  {bold('Expires:')}      {yellow(link.expires_at)}")
    if link.max_clicks:
        print(f"  {bold('Max Clicks:')}   {link.max_clicks}")

    if args.qr:
        print(f"\n  {bold('QR Code:')}")
        qr = QRCode(short_url)
        print(qr.to_terminal())

    print()
    return 0


def cmd_resolve(args: argparse.Namespace, service: LinkService) -> int:
    try:
        link = service.resolve(args.code)
    except (LinkNotFoundError, LinkExpiredError) as err:
        if args.json:
            print(json.dumps({"error": str(err)}))
        else:
            print(red(f"Error: {err}"), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(link.to_dict(), indent=2))
        return 0

    print(f"\n  {bold('Code:')}        {cyan(link.code)}")
    print(f"  {bold('Target URL:')}  {link.target_url}")
    print(f"  {bold('Total Clicks:')}{link.click_count}")
    print(f"  {bold('Status:')}      {green('Active')}\n")
    return 0


def cmd_stats(args: argparse.Namespace, db: Database) -> int:
    engine = AnalyticsEngine(db)
    stats = engine.get_link_stats(args.code)
    if stats is None:
        if args.json:
            print(json.dumps({"error": f"Short code '{args.code}' not found."}))
        else:
            print(red(f"Error: Short code '{args.code}' not found."), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(stats.to_dict(), indent=2))
        return 0

    link = stats.link
    status = red("Expired") if link.is_expired() else green("Active")

    print(bold(cyan(f"\n⚡ Analytics for code: {link.code}")))
    print(f"  Destination: {link.target_url}")
    print(f"  Status:      {status}  |  Total Clicks: {bold(str(stats.total_clicks))}  |  Unique Visitors: {bold(str(stats.unique_visitors))}")

    # Daily distribution chart
    if stats.clicks_by_date:
        print(bold(yellow("\n📅 Daily Click Volume:")))
        max_c = max(stats.clicks_by_date.values())
        for date, count in stats.clicks_by_date.items():
            bar = render_bar(count, max_c, width=20)
            print(f"  {date} | {cyan(bar)} {count}")

    # Top referrers
    if stats.top_referrers:
        print(bold(yellow("\n🌐 Top Referrers:")))
        for ref, count in stats.top_referrers:
            print(f"  • {ref:<25} {bold(str(count))} clicks")

    # Browsers & Devices
    if stats.browsers or stats.devices:
        print(bold(yellow("\n💻 Browsers & Devices:")))
        browser_str = ", ".join(f"{b}: {c}" for b, c in stats.browsers.items())
        device_str = ", ".join(f"{d}: {c}" for d, c in stats.devices.items())
        print(f"  Browsers: {browser_str}")
        print(f"  Devices:  {device_str}")

    print()
    return 0


def cmd_list(args: argparse.Namespace, service: LinkService) -> int:
    links = service.list_links(limit=args.limit, offset=args.offset)
    if args.json:
        print(json.dumps([l.to_dict() for l in links], indent=2))
        return 0

    if not links:
        print(dim("No shortened links found in database."))
        return 0

    print(bold(cyan(f"\n{'CODE':<10} {'CLICKS':<8} {'STATUS':<10} {'DESTINATION':<40}")))
    print("-" * 72)
    for l in links:
        status_txt = red("Expired") if l.is_expired() else green("Active")
        dest = l.target_url if len(l.target_url) <= 38 else l.target_url[:35] + "..."
        print(f"{bold(l.code):<10} {l.click_count:<8} {status_txt:<19} {dest}")
    print()
    return 0


def cmd_qr(args: argparse.Namespace, service: LinkService) -> int:
    try:
        link = service.resolve(args.code)
    except (LinkNotFoundError, LinkExpiredError) as err:
        print(red(f"Error: {err}"), file=sys.stderr)
        return 1

    short_url = f"{args.base_url.rstrip('/')}/{link.code}"
    qr = QRCode(short_url)

    if args.svg:
        svg_content = qr.to_svg()
        with open(args.svg, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(green(f"✔ QR code saved to SVG: {args.svg}"))
        return 0

    print(bold(cyan(f"\nQR Code for: {short_url}")))
    if args.ascii:
        print(qr.to_ascii())
    else:
        print(qr.to_terminal())
    return 0


def cmd_delete(args: argparse.Namespace, service: LinkService) -> int:
    if not args.force:
        confirm = input(f"Delete short link '{args.code}'? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return 0

    success = service.delete(args.code)
    if args.json:
        print(json.dumps({"deleted": success, "code": args.code}))
    else:
        if success:
            print(green(f"✔ Short link '{args.code}' deleted."))
        else:
            print(yellow(f"No link found with code '{args.code}'."))
    return 0 if success else 1


def cmd_bulk(args: argparse.Namespace, service: LinkService) -> int:
    if not os.path.exists(args.file):
        print(red(f"Error: File not found: '{args.file}'"), file=sys.stderr)
        return 1

    items = []
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("[") or content.startswith("{"):
                parsed = json.loads(content)
                items = parsed if isinstance(parsed, list) else parsed.get("items", [])
            else:
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        items.append({"url": line})
    except Exception as err:
        print(red(f"Error parsing file: {err}"), file=sys.stderr)
        return 1

    results = service.bulk_shorten(items)
    for r in results:
        if r.get("success") and "code" in r:
            r["short_url"] = f"{args.base_url.rstrip('/')}/{r['code']}"

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    print(bold(cyan(f"\n⚡ Bulk Shortened {len(results)} URLs:")))
    print(f"{'STATUS':<8} {'CODE':<10} {'SHORT URL':<30} {'DESTINATION'}")
    print("-" * 75)
    for r in results:
        if r.get("success"):
            dest = r["target_url"] if len(r["target_url"]) <= 30 else r["target_url"][:27] + "..."
            print(f"{green('OK'):<17} {bold(r['code']):<10} {r['short_url']:<30} {dest}")
        else:
            print(f"{red('FAIL'):<17} {'-':<10} {'-':<30} {r.get('url')} ({r.get('error')})")
    print()
    return 0


def cmd_export(args: argparse.Namespace, db: Database) -> int:
    clicks = db.get_clicks_for_link(args.code)
    if args.format == "csv":
        from nanolink.core.export import export_clicks_to_csv
        result = export_clicks_to_csv(clicks)
    else:
        from nanolink.core.analytics import AnalyticsEngine
        from nanolink.core.export import export_stats_to_json
        stats = AnalyticsEngine(db).get_link_stats(args.code)
        if stats is None:
            print(red(f"Error: Link '{args.code}' not found."), file=sys.stderr)
            return 1
        result = export_stats_to_json(stats)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(green(f"✔ Exported {len(clicks)} records to {args.output}"))
    else:
        print(result)
    return 0


def cmd_search(args: argparse.Namespace, service: LinkService) -> int:
    links = service.search_links(args.query, limit=args.limit)
    if args.json:
        print(json.dumps([l.to_dict() for l in links], indent=2))
        return 0

    if not links:
        print(dim(f"No links matched query '{args.query}'."))
        return 0

    print(bold(cyan(f"\n⚡ Search Results for '{args.query}' ({len(links)} matches):")))
    print(f"{'CODE':<10} {'CLICKS':<8} {'TAGS':<18} {'DESTINATION'}")
    print("-" * 75)
    for l in links:
        tags_str = ",".join(l.tags) if l.tags else "-"
        dest = l.target_url if len(l.target_url) <= 35 else l.target_url[:32] + "..."
        print(f"{bold(l.code):<10} {l.click_count:<8} {dim(tags_str):<18} {dest}")
    print()
    return 0


def cmd_backup(args: argparse.Namespace, db: Database) -> int:
    try:
        db.backup(args.target)
        size = Path(args.target).stat().st_size
        print(bold(green(f"✔ Backup successfully created: {args.target} ({size} bytes)")))
        return 0
    except Exception as err:
        print(red(f"Backup failed: {err}"), file=sys.stderr)
        return 1


def cmd_vacuum(args: argparse.Namespace, db: Database) -> int:
    before = db.get_db_size()
    db.vacuum()
    after = db.get_db_size()
    saved = max(0, before - after)
    print(bold(green("✔ Database vacuumed and optimized successfully.")))
    if before > 0:
        print(f"  Size before: {before} bytes | Size after: {after} bytes ({saved} bytes reclaimed)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    db = Database(args.db)
    service = LinkService(db)

    if args.command == "shorten":
        return cmd_shorten(args, service)
    elif args.command == "resolve":
        return cmd_resolve(args, service)
    elif args.command == "stats":
        return cmd_stats(args, db)
    elif args.command == "list":
        return cmd_list(args, service)
    elif args.command == "qr":
        return cmd_qr(args, service)
    elif args.command == "delete":
        return cmd_delete(args, service)
    elif args.command == "bulk":
        return cmd_bulk(args, service)
    elif args.command == "export":
        return cmd_export(args, db)
    elif args.command == "search":
        return cmd_search(args, service)
    elif args.command == "backup":
        return cmd_backup(args, db)
    elif args.command == "vacuum":
        return cmd_vacuum(args, db)
    elif args.command == "serve":
        from nanolink.server.handler import run_server
        return run_server(host=args.host, port=args.port, db=db)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
