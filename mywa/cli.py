"""Command line interface for the mywa toolkit."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .ingest import ingest
from .segmenter import deduplicate, opportunities, segment
from .exporters import export_csv, export_json, export_report, export_vcf
from .callerid import build_directory, enrich as caller_enrich, stats as caller_stats


def _parse_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    return [k.strip() for k in value.replace(";", ",").split(",") if k.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mywa",
        description="Extract, dedupe and segment every WhatsApp contact "
                    "(including group members) from msgstore.db, wa.db, VCF "
                    "files or ADB dumps.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--input", "-i", nargs="+", required=True,
        help="Input file(s) or folder(s). Auto-detects *.db (msgstore/wa), "
             "*.vcf and *.tsv.",
    )
    parser.add_argument(
        "--out", "-o", default="out",
        help="Output directory (default: out).",
    )
    parser.add_argument(
        "--country-code", default="GH",
        help="Default country code for local numbers (default: GH = +233).",
    )
    parser.add_argument(
        "--country-number", dest="country_number", default=None,
        help="E.164 country dial code matching --country-code (default derived).",
    )
    parser.add_argument(
        "--opportunity-groups", default=None,
        help="Comma-separated keywords for targeted opportunity tagging, e.g. "
             "'real estate, wholesale, import'.",
    )
    parser.add_argument(
        "--min-activity", default="cold",
        choices=["hot", "warm", "recent", "cold"],
        help="Minimum activity level to include in opportunities (default: cold).",
    )
    parser.add_argument(
        "--contacts-only", action="store_true",
        help="Skip the opportunities/report generation.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print summary counts without writing files.",
    )
    parser.add_argument(
        "--serve", nargs="?", const=8000, type=int, metavar="PORT",
        help="Start the local web dashboard after processing (default port 8000).",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open the dashboard in your browser when --serve is used.",
    )
    parser.add_argument(
        "--lookup", default="",
        metavar="PROVIDERS",
        help="OPTIONAL hybrid enrichment (off by default = zero cost). Comma list: "
             "opencnam, endpoint, all. E.g.: --lookup all",
    )
    parser.add_argument(
        "--lookup-endpoint", default="",
        help="Base URL of a self-hosted/cheap lookup API to enrich 'endpoint'.",
    )
    parser.add_argument(
        "--lookup-key", default="",
        help="API key for --lookup-endpoint, if required.",
    )
    parser.add_argument(
        "--lookup-cache", default=".lookup_cache",
        help="Directory to cache lookup results (avoids repeat provider charges).",
    )
    parser.add_argument(
        "--lookup-delay", type=float, default=0.1,
        help="Seconds to pause between provider calls (rate control).",
    )
    parser.add_argument(
        "--analyze", action="store_true",
        help="After processing, run the revenue agent on the output "
             "(writes revenue_out/revenue.json + revenue_report.html).",
    )
    parser.add_argument(
        "--revenue-dir", default="revenue_out",
        help="Where the revenue agent writes its report (default: revenue_out).",
    )
    return parser


def _resolve_country_number(code: str) -> str:
    table = {
        "GH": "233", "NG": "234", "ZA": "27", "KE": "254",
        "TZ": "255", "UG": "256", "EG": "20", "MA": "212",
        "US": "1", "GB": "44", "IN": "91", "DE": "49", "FR": "33",
    }
    return table.get(code.upper(), code)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    country_number = args.country_number or _resolve_country_number(args.country_code)

    print(f"mywa v{__version__} | country +{country_number}")
    raw = ingest(args.input)
    print(f"ingested {len(raw)} raw contact records")
    if not raw:
        print("no contacts extracted. Check --help for accepted inputs.")
        return 2

    contacts = deduplicate(raw, country_number)
    print(f"{len(contacts)} unique contacts after deduplication")

    keywords = _parse_keywords(args.opportunity_groups)
    segmented = segment(contacts, country_number, opportunity_keywords=keywords)
    valid = sum(1 for s in segmented if s.valid)
    print(f"{valid} valid mobile numbers, {len(segmented) - valid} invalid/landline")
    if keywords:
        tags = sum(1 for s in segmented if s.group_tags)
        print(f"{tags} contacts tagged with opportunity group keywords")

    cdir = build_directory(contacts)
    caller_enrich(segmented, cdir)
    cstats = caller_stats(segmented)
    if cstats["unnamed"]:
        print(f"caller-id: {cstats['unnamed']} unnamed -> "
              f"{cstats['identified']} identified, {cstats['unknown']} unknown")

    if args.lookup and (args.lookup != "off"):
        from .lookup import run_lookups
        looked, resolved = run_lookups(
            segmented, cdir, args.lookup, args.lookup_endpoint, args.lookup_key,
            args.lookup_cache, args.lookup_delay,
        )
        print(f"lookup: queried providers for {looked} unknown numbers, "
              f"{resolved} enriched (results cached in {args.lookup_cache})")

    if args.dry_run:
        print("dry run complete (no files written)")
        return 0

    os.makedirs(args.out, exist_ok=True)
    export_csv(os.path.join(args.out, "contacts.csv"), segmented)
    export_vcf(os.path.join(args.out, "contacts.vcf"), contacts)
    export_json(os.path.join(args.out, "contacts.json"), segmented)
    print(f"wrote contacts.csv, contacts.vcf, contacts.json -> {args.out}")

    if not args.contacts_only:
        opps = opportunities(segmented, keywords, min_activity=args.min_activity)
        opps_sorted = sorted(
            opps,
            key=lambda s: (s.activity != "hot", s.activity != "warm",
                           -s.contact.msg_count),
        )
        export_csv(os.path.join(args.out, "opportunities.csv"), opps_sorted)
        export_report(os.path.join(args.out, "report.html"), segmented, opps_sorted)
        print(f"wrote opportunities.csv ({len(opps_sorted)}) + report.html -> {args.out}")

    if args.analyze:
        from .revenue import analyze as analyze_revenue
        analyze_revenue(args.out, args.revenue_dir)
        print(f"revenue agent -> {args.revenue_dir}/revenue.json + revenue_report.html")

    if args.serve is not None:
        from .server import serve
        try:
            serve(args.out, port=args.serve, launch=args.open)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
