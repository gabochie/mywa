"""Export segmented contacts to CSV, VCF, JSON and a standalone HTML report."""
from __future__ import annotations

import csv
import html
import json
import os
from collections import Counter
from .models import Contact, SegmentedContact

FIELD_NAMES = [
    "name", "phone", "country", "carrier", "valid", "named", "caller",
    "diaspora", "lookup", "lookup_src", "line", "activity",
    "origin", "org", "email", "address", "city", "home_country", "website",
    "groups", "group_tags", "my_contact", "is_business", "is_admin", "labels",
    "msg_count", "sent_count", "last_seen", "source",
]


def _rows(segmented: list[SegmentedContact]) -> list[dict]:
    return [s.row() for s in segmented]


def export_csv(path: str, segmented: list[SegmentedContact]) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELD_NAMES)
        writer.writeheader()
        writer.writerows(_rows(segmented))
    return path


def export_vcf(path: str, contacts: list[Contact]) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", errors="replace") as fh:
        for c in contacts:
            name = (c.name or c.primary_number()).strip()
            fh.write("BEGIN:VCARD\r\n")
            fh.write("VERSION:3.0\r\n")
            fh.write(f"FN:{name}\r\n")
            fh.write(f"N:{name};;;;\r\n")
            if c.org:
                fh.write(f"ORG:{c.org}\r\n")
            for n in c.numbers:
                fh.write(f"TEL;TYPE=CELL:{n}\r\n")
            for e in c.emails:
                fh.write(f"EMAIL:{e}\r\n")
            for g in c.groups:
                fh.write(f"CATEGORIES:{g}\r\n")
            fh.write("END:VCARD\r\n")
    return path


def export_json(path: str, segmented: list[SegmentedContact]) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = {
        "generated": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "count": len(segmented),
        "contacts": _rows(segmented),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


def _group_stats(segmented: list[SegmentedContact]) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for s in segmented:
        for g in s.contact.groups:
            counter[g] += 1
    return counter.most_common(40)


def _summary(segmented: list[SegmentedContact]) -> dict:
    total = len(segmented)
    valid = sum(1 for s in segmented if s.valid)
    by_country = Counter(s.country or "Unknown" for s in segmented)
    by_activity = Counter(s.activity for s in segmented)
    by_origin = Counter(s.origin for s in segmented)
    by_carrier = Counter(s.carrier or "Unknown" for s in segmented)
    return {
        "total": total,
        "valid": valid,
        "invalid": total - valid,
        "by_country": dict(by_country),
        "by_activity": dict(by_activity),
        "by_origin": dict(by_origin),
        "by_carrier": dict(by_carrier),
    }


def export_report(path: str, segmented: list[SegmentedContact],
                  opportunities: list[SegmentedContact]) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    s = _summary(segmented)
    table_rows = "".join(
        f"<tr><td>{html.escape(r['name'])}</td><td>{html.escape(r['phone'])}</td>"
        f"<td>{html.escape(r['carrier'])}</td><td>{html.escape(r['activity'])}</td>"
        f"<td>{html.escape(r['origin'])}</td>"
        f"<td>{html.escape(r['group_tags'] or r['groups'])}</td></tr>"
        for r in _rows(opportunities)
    ) or "<tr><td colspan='6'>No opportunities matched the filter.</td></tr>"

    group_rows = "".join(
        f"<tr><td>{html.escape(g)}</td><td>{n}</td></tr>"
        for g, n in _group_stats(segmented)
    ) or "<tr><td colspan='2'>No groups found.</td></tr>"

    def stats_block(items: dict) -> str:
        return "".join(
            f"<span class='chip'>{html.escape(str(k))}: <b>{v}</b></span>" for k, v in items.items()
        )

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>mywa Contact Report</title>
<style>
 body{{font-family:'Segoe UI',Arial,sans-serif;margin:2rem;color:#1f2937;background:#f9fafb}}
 h1{{color:#075E54}} .cards{{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}}
 .card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:1rem 1.25rem;min-width:140px;box-shadow:0 1px 2px rgba(0,0,0,.05)}}
 .card b{{font-size:1.6rem;display:block}}
 .chip{{display:inline-block;background:#e7f4f1;color:#075E54;border-radius:999px;padding:.25rem .75rem;margin:.15rem}}
 table{{border-collapse:collapse;width:100%;background:#fff;margin-top:.5rem}}
 th,td{{text-align:left;padding:.5rem .75rem;border-bottom:1px solid #e5e7eb}}
 th{{background:#075E54;color:#fff}} tr:nth-child(even){{background:#f3faf8}}
 h2{{margin-top:2rem}}
</style></head><body>
<h1>WhatsApp Contact Intelligence Report</h1>
<div class="cards">
 <div class="card"><b>{s['total']}</b>Total contacts</div>
 <div class="card"><b>{s['valid']}</b>Valid mobile</div>
 <div class="card"><b>{s['invalid']}</b>Invalid / landline</div>
</div>
<h2>Segment breakdown</h2>
<div class="cards">
 <div class="card"><b>Country</b>{stats_block(s['by_country'])}</div>
 <div class="card"><b>Carrier</b>{stats_block(s['by_carrier'])}</div>
 <div class="card"><b>Activity</b>{stats_block(s['by_activity'])}</div>
 <div class="card"><b>Origin</b>{stats_block(s['by_origin'])}</div>
</div>
<h2>Targeted opportunities ({len(opportunities)})</h2>
<table><tr><th>Name</th><th>Phone</th><th>Carrier</th><th>Activity</th><th>Origin</th><th>Group</th></tr>
{table_rows}</table>
<h2>Top groups</h2>
<table><tr><th>Group</th><th>Members</th></tr>{group_rows}</table>
</body></html>"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return path
