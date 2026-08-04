"""Revenue Agent — analyze segmented contacts and project monetization potential.

Reads the segmented contacts.json from the pipeline output and generates:
  - Per-segment revenue projections (GHS)
  - Recommended products/services per segment
  - Priority-ranked outreach playbook
  - Strategy report (JSON + HTML)

Usage:
    python -m mywa.revenue --out real_out --output-dir revenue_out
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Product catalog — what we can sell
# ---------------------------------------------------------------------------

PRODUCTS: list[dict[str, Any]] = [
    {
        "id": "waba_campaign",
        "name": "WhatsApp Marketing Campaign",
        "desc": "Bulk broadcast to segmented list with rich media (image, video, catalog).",
        "model": "per_contact",
        "price": 0.50,
        "min": 100,
        "delivery": "1-2 days",
        "target_activity": ["hot", "warm", "recent"],
        "target_origin": ["direct_and_group", "direct", "group_only"],
        "conv": {"hot": 0.15, "warm": 0.08, "recent": 0.03, "cold": 0.01},
    },
    {
        "id": "lead_gen",
        "name": "Lead Generation Package",
        "desc": "Curated lead list with contact details, business info, engagement scoring.",
        "model": "flat",
        "price": 500,
        "batch": 50,
        "delivery": "3-5 days",
        "target_activity": ["hot", "warm"],
        "target_origin": ["direct_and_group", "direct"],
        "conv": {"hot": 0.20, "warm": 0.10, "recent": 0.04, "cold": 0.01},
    },
    {
        "id": "crm_setup",
        "name": "WhatsApp CRM Setup",
        "desc": "Full CRM integration: auto-categorize, trigger sequences, reply triage.",
        "model": "flat",
        "price": 2000,
        "delivery": "5-7 days",
        "target_activity": ["hot", "warm"],
        "target_origin": ["direct_and_group"],
        "conv": {"hot": 0.25, "warm": 0.12, "recent": 0.03, "cold": 0.005},
    },
    {
        "id": "data_enrichment",
        "name": "Contact Enrichment Service",
        "desc": "Fill missing data: names, emails, business info, social profiles, caller-ID.",
        "model": "per_contact",
        "price": 0.20,
        "min": 500,
        "delivery": "2-3 days",
        "target_activity": ["cold", "recent", "warm"],
        "target_origin": ["group_only", "derived"],
        "conv": {"hot": 0.05, "warm": 0.05, "recent": 0.04, "cold": 0.02},
    },
    {
        "id": "group_broadcast",
        "name": "Group Broadcast Service",
        "desc": "Post targeted messages in relevant WhatsApp groups (real estate, wholesale).",
        "model": "per_group",
        "price": 100,
        "delivery": "1 day",
        "target_activity": ["hot", "warm", "recent", "cold"],
        "target_origin": ["group_only", "direct_and_group"],
        "conv": {"hot": 0.10, "warm": 0.06, "recent": 0.02, "cold": 0.005},
    },
    {
        "id": "diaspora_connect",
        "name": "Diaspora Connection Service",
        "desc": "Connect Ghana-based businesses with diaspora buyers/investors.",
        "model": "flat",
        "price": 1500,
        "delivery": "7-14 days",
        "target_activity": ["hot", "warm", "recent"],
        "target_origin": ["direct_and_group", "direct"],
        "conv": {"hot": 0.12, "warm": 0.06, "recent": 0.02, "cold": 0.005},
    },
    {
        "id": "real_estate_leads",
        "name": "Real Estate Lead Pack",
        "desc": "Curated real estate investor/buyer leads with interest profiling.",
        "model": "flat",
        "price": 800,
        "batch": 25,
        "delivery": "3-5 days",
        "target_activity": ["hot", "warm"],
        "target_origin": ["group_only", "direct_and_group"],
        "conv": {"hot": 0.18, "warm": 0.09, "recent": 0.03, "cold": 0.01},
    },
    {
        "id": "wholesale_match",
        "name": "Wholesale Matchmaking",
        "desc": "Connect wholesalers with retailers/buyers. Curated match list.",
        "model": "per_match",
        "price": 50,
        "delivery": "2-3 days",
        "target_activity": ["hot", "warm", "recent"],
        "target_origin": ["group_only", "direct_and_group"],
        "conv": {"hot": 0.15, "warm": 0.08, "recent": 0.03, "cold": 0.01},
    },
]

# ---------------------------------------------------------------------------
# Industry verticals -- what to sell to whom
# ---------------------------------------------------------------------------

VERTICALS: dict[str, dict[str, Any]] = {
    "real_estate": {
        "keywords": ["real_estate", "real estate", "property", "apartment", "house",
                     "land", "estate", "real_estate_agency", "real_estate_agent",
                     "real_estate_developer", "real_estate_consultant", "realtor",
                     "commercial_real_estate", "industrial_real_estate", "estate_agent"],
        "products": ["real_estate_leads", "waba_campaign", "diaspora_connect", "crm_setup"],
        "avg_deal": 50000,
        "cycle_days": 30,
        "priority": "high",
    },
    "construction": {
        "keywords": ["construction", "building", "contractor", "engineer", "roofing",
                     "plumbing", "electrical", "general_contractor", "construction_company",
                     "construction_equipment_supplier", "machine_construction",
                     "building_materials"],
        "products": ["lead_gen", "waba_campaign", "group_broadcast"],
        "avg_deal": 25000,
        "cycle_days": 45,
        "priority": "high",
    },
    "wholesale_retail": {
        "keywords": ["wholesale", "wholesaler", "distributor", "retail", "shop", "store",
                     "market", "supplier", "import", "exporter", "office_supply",
                     "pharmaceutical_products_wholesaler", "logistics"],
        "products": ["wholesale_match", "waba_campaign", "lead_gen"],
        "avg_deal": 15000,
        "cycle_days": 14,
        "priority": "high",
    },
    "hospitality": {
        "keywords": ["hotel", "lodge", "guest_house", "airbnb", "accommodation",
                     "restaurant", "food", "cafe", "bar", "guesthouse", "resort"],
        "products": ["waba_campaign", "lead_gen", "data_enrichment"],
        "avg_deal": 8000,
        "cycle_days": 21,
        "priority": "medium",
    },
    "healthcare": {
        "keywords": ["hospital", "clinic", "pharmacy", "medical", "health", "doctor",
                     "dental", "pharma", "medical_center", "medical_clinic"],
        "products": ["waba_campaign", "lead_gen", "crm_setup"],
        "avg_deal": 12000,
        "cycle_days": 30,
        "priority": "medium",
    },
    "beauty_fashion": {
        "keywords": ["salon", "spa", "beauty", "hair", "nail", "barber", "fashion",
                     "clothing", "cosmetics", "makeup", "beauty_salon", "barber_shop"],
        "products": ["waba_campaign", "group_broadcast", "lead_gen"],
        "avg_deal": 5000,
        "cycle_days": 7,
        "priority": "medium",
    },
    "automotive": {
        "keywords": ["car", "auto", "motor", "vehicle", "tyre", "tire", "mechanic",
                     "auto_parts", "car_repair", "car_dealer", "car_rental"],
        "products": ["waba_campaign", "lead_gen", "group_broadcast"],
        "avg_deal": 10000,
        "cycle_days": 14,
        "priority": "medium",
    },
    "agriculture": {
        "keywords": ["farm", "agro", "agricultur", "crop", "livestock", "ranch",
                     "fisher", "garden", "rabbit", "poultry"],
        "products": ["waba_campaign", "wholesale_match", "lead_gen"],
        "avg_deal": 8000,
        "cycle_days": 30,
        "priority": "medium",
    },
    "logistics": {
        "keywords": ["logistics", "freight", "shipping", "courier", "cargo", "transport",
                     "delivery", "storage", "supply chain"],
        "products": ["waba_campaign", "lead_gen", "crm_setup"],
        "avg_deal": 18000,
        "cycle_days": 21,
        "priority": "medium",
    },
    "furniture_decor": {
        "keywords": ["furniture", "decor", "interior", "home_goods", "upholstery",
                     "wood", "home decor", "furniture_store"],
        "products": ["waba_campaign", "lead_gen", "group_broadcast"],
        "avg_deal": 7000,
        "cycle_days": 10,
        "priority": "medium",
    },
    "tech_it": {
        "keywords": ["software", "it ", "tech", "digital", "internet", "web", "app",
                     "systems", "computer", "telecom", "electronics", "solar"],
        "products": ["waba_campaign", "lead_gen", "crm_setup"],
        "avg_deal": 20000,
        "cycle_days": 21,
        "priority": "high",
    },
}

COUNTRY_TIER = {"GH": "home", "US": "diaspora", "GB": "diaspora", "ZA": "diaspora",
                "NG": "diaspora", "IN": "diaspora", "CN": "diaspora", "": "unknown"}

ACTIVITY_WEIGHT = {"hot": 1.0, "warm": 0.6, "recent": 0.25, "cold": 0.05}

ORIGIN_WEIGHT = {"direct_and_group": 1.0, "direct": 0.8, "group_only": 0.5, "saved": 0.4, "derived": 0.15}

# Per-contract pricing tiers (GHS) for the "agency" model
CONTRACT_TIERS = [
    {"name": "Discovery", "price": 500, "scope": "Data audit + segment report"},
    {"name": "Starter", "price": 1500, "scope": "1 campaign + 1 segment"},
    {"name": "Growth", "price": 4000, "scope": "3 campaigns + CRM + dashboard"},
    {"name": "Scale", "price": 10000, "scope": "Unlimited campaigns + dedicated manager"},
    {"name": "Enterprise", "price": 25000, "scope": "Full pipeline + integration + SLA"},
]


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    return (s or "").lower().strip()


def _match_vertical(c: dict) -> tuple[str, float]:
    """Return (vertical_id, score) for a contact based on group/org signals."""
    signals = []
    for g in (c.get("groups") or "").split(";"):
        signals.append(_norm(g))
    for t in (c.get("group_tags") or "").split(";"):
        signals.append(_norm(t))
    org = _norm(c.get("org") or "")
    name = _norm(c.get("name") or "")
    if org:
        signals.append(org)
    if name:
        signals.append(name)

    best_id, best_score = "", 0.0
    for vid, v in VERTICALS.items():
        score = 0.0
        for kw in v["keywords"]:
            kw = kw.strip().lower()
            if not kw:
                continue
            for s in signals:
                if kw in s:
                    # keyword length weighted: longer, more specific match = stronger
                    score += min(len(kw) / 20.0, 1.0)
                    break
        if score > best_score:
            best_id, best_score = vid, score
    return best_id, best_score


def _value_score(c: dict) -> float:
    """Composite lead score 0..1 driving priority ordering."""
    activity = ACTIVITY_WEIGHT.get(c.get("activity"), 0.05)
    origin = ORIGIN_WEIGHT.get(c.get("origin"), 0.15)
    named = 1.0 if c.get("named") else 0.3
    business = 1.0 if c.get("is_business") else 0.6
    diaspora = 1.3 if c.get("diaspora") else 1.0
    email = 1.1 if (c.get("email") or "").strip() else 1.0
    msgs = min(c.get("msg_count") or 0, 100) / 100.0
    score = (0.35 * activity + 0.20 * origin + 0.10 * named +
             0.10 * business + 0.15 * diaspora + 0.05 * email + 0.05 * msgs)
    return round(min(score * diaspora, 1.0), 3)


def _product_price(p: dict, count: int) -> float:
    if p["model"] == "flat":
        batches = max(1, int((count + (p.get("batch") or 1) - 1) / (p.get("batch") or 1)))
        return p["price"] * batches
    if p["model"] == "per_contact":
        return p["price"] * max(count, p.get("min") or 0)
    if p["model"] == "per_match":
        return p["price"] * count
    if p["model"] == "per_group":
        return p["price"] * count
    return 0.0


def _product_revenue(p: dict, eligible: list[dict], conversion: float) -> float:
    return round(_product_price(p, len(eligible)) * conversion, 0)


class RevenueAgent:
    """Analyzes segmented contacts and projects monetization."""

    def __init__(self, contacts: list[dict], out_dir: str = "revenue_out",
                 currency: str = "GHS"):
        self.contacts = list(contacts)
        self.out_dir = out_dir
        self.currency = currency
        self.now = datetime.now(timezone.utc).isoformat() + "Z"

    # -- segmentation ------------------------------------------------------

    def _by_activity(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for c in self.contacts:
            out.setdefault(c.get("activity") or "cold", []).append(c)
        return out

    def _by_country(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for c in self.contacts:
            out.setdefault(c.get("country") or "Unknown", []).append(c)
        return out

    def _by_vertical(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for c in self.contacts:
            vid, score = _match_vertical(c)
            if vid and score > 0:
                out.setdefault(vid, []).append(c)
        return out

    # -- projections -------------------------------------------------------

    def analyze(self) -> dict[str, Any]:
        by_activity = self._by_activity()
        by_country = self._by_country()
        by_vertical = self._by_vertical()

        # per-contact scoring for the playbook
        scored = []
        for c in self.contacts:
            c = dict(c)
            c["_value"] = _value_score(c)
            c["_vertical"], c["_vscore"] = _match_vertical(c)
            scored.append(c)
        scored.sort(key=lambda x: (-x["_value"], -(x.get("msg_count") or 0)))

        # revenue projection per activity segment per product
        segment_projection = {}
        for act, members in by_activity.items():
            prods = []
            for p in PRODUCTS:
                eligible = [c for c in members
                            if act in p["target_activity"] and
                            c.get("origin") in p["target_origin"]]
                if not eligible:
                    continue
                revenue = _product_revenue(p, eligible, p["conv"][act])
                prods.append({
                    "product": p["name"],
                    "count": len(eligible),
                    "price": p["price"],
                    "conversion": p["conv"][act],
                    "revenue": revenue,
                    "model": p["model"],
                })
            prods.sort(key=lambda x: -x["revenue"])
            segment_projection[act] = {
                "count": len(members),
                "products": prods,
                "best_revenue": prods[0]["revenue"] if prods else 0,
            }

        # vertical projections
        vertical_projection = {}
        for vid, members in by_vertical.items():
            v = VERTICALS[vid]
            engaged = [c for c in members
                       if c.get("activity") in ("hot", "warm", "recent")]
            pipeline = round(v["avg_deal"] * len(engaged) *
                             min(0.02 + 0.01 * len(engaged) / 100.0, 0.20))
            vertical_projection[vid] = {
                "name": vid.replace("_", " ").title(),
                "count": len(members),
                "engaged": len(engaged),
                "avg_deal": v["avg_deal"],
                "cycle_days": v["cycle_days"],
                "priority": v["priority"],
                "pipeline": pipeline,
                "products": v["products"],
            }

        # country / diaspora projection
        country_projection = {}
        for country, members in by_country.items():
            tier = COUNTRY_TIER.get(country, "other")
            country_projection[country] = {
                "count": len(members),
                "tier": tier,
                "businesses": sum(1 for c in members if c.get("is_business")),
                "emails": sum(1 for c in members if (c.get("email") or "").strip()),
                "with_website": sum(1 for c in members if (c.get("website") or "").strip()),
            }

        # top playbook entries
        top = scored[:50]
        playbook = []
        for i, c in enumerate(top, 1):
            vid = c["_vertical"]
            products = VERTICALS[vid]["products"] if vid in VERTICALS else ["waba_campaign"]
            product_names = [next((p["name"] for p in PRODUCTS if p["id"] == pid), pid)
                             for pid in products]
            playbook.append({
                "rank": i,
                "name": c.get("name") or (c.get("caller") or "Unnamed"),
                "phone": c.get("phone"),
                "country": c.get("country"),
                "activity": c.get("activity"),
                "origin": c.get("origin"),
                "msg_count": c.get("msg_count") or 0,
                "is_business": bool(c.get("is_business")),
                "diaspora": bool(c.get("diaspora")),
                "vertical": vid or "general",
                "value_score": c["_value"],
                "email": c.get("email") or "",
                "website": c.get("website") or "",
                "groups": c.get("groups") or "",
                "sell": product_names,
            })

        # ---- multi-channel revenue model ----
        valid = [c for c in self.contacts if c.get("valid")]
        businesses = [c for c in self.contacts if c.get("is_business")]
        consumers = [c for c in self.contacts if not c.get("is_business")]
        diaspora = [c for c in self.contacts if c.get("diaspora")]
        hot_warm = [c for c in self.contacts
                    if c.get("activity") in ("hot", "warm")]

        # B2B channel: sell services to businesses (lead gen, campaigns, CRM)
        # Realistic close-rate curve: cheaper tiers close more often.
        b2b_clients_total = 0
        b2b_revenue = 0.0
        b2b_tiers = []
        for tier in CONTRACT_TIERS:
            rate = {"Discovery": 0.005, "Starter": 0.0025, "Growth": 0.0010,
                    "Scale": 0.0003, "Enterprise": 0.0001}.get(tier["name"], 0.001)
            clients = round(len(businesses) * rate)
            b2b_clients_total += clients
            b2b_revenue += clients * tier["price"]
            b2b_tiers.append({
                "name": tier["name"],
                "price": tier["price"],
                "scope": tier["scope"],
                "clients": clients,
                "revenue": round(clients * tier["price"], 0),
            })

        # B2C channel: campaign fees per hot/warm consumer lead
        b2c_reach = len(hot_warm)
        b2c_revenue = round(b2c_reach * 0.5 * 0.15)  # 0.5 GHS/contact x 15% conv

        # Diaspora channel: real estate / remittance services to diaspora
        dia_reach = len(diaspora)
        dia_revenue = round(dia_reach * 50 * 0.02)  # 50 GHS avg fee x 2% conv

        # Contract tier projection (B2B only)
        contract_revenue = b2b_revenue

        total_product_revenue = sum(
            p["revenue"]
            for seg in segment_projection.values()
            for p in seg["products"]
        )
        total_revenue = (total_product_revenue + contract_revenue +
                         b2c_revenue + dia_revenue)

        return {
            "generated": self.now,
            "currency": self.currency,
            "summary": {
                "total_contacts": len(self.contacts),
                "valid_contacts": len(valid),
                "hot": len(by_activity.get("hot", [])),
                "warm": len(by_activity.get("warm", [])),
                "recent": len(by_activity.get("recent", [])),
                "businesses": len(businesses),
                "consumers": len(consumers),
                "emails": sum(1 for c in self.contacts if (c.get("email") or "").strip()),
                "with_website": sum(1 for c in self.contacts if (c.get("website") or "").strip()),
                "diaspora": len(diaspora),
                "verticals": {k: len(v) for k, v in by_vertical.items()},
                "channels": {
                    "b2b": {
                        "clients": b2b_clients_total,
                        "avg_contract": round(b2b_revenue / max(1, b2b_clients_total), 0),
                        "revenue": round(b2b_revenue, 0),
                        "tiers": b2b_tiers,
                    },
                    "b2c_campaigns": {"reach": b2c_reach, "revenue": b2c_revenue},
                    "diaspora": {"reach": dia_reach, "revenue": dia_revenue},
                    "product_services": {"revenue": round(total_product_revenue, 0)},
                },
                "est_total_revenue": round(total_revenue, 0),
            },
            "segments": {
                "by_activity": segment_projection,
                "by_country": country_projection,
                "by_vertical": vertical_projection,
            },
            "playbook": playbook,
        }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _fmt_g(n: float) -> str:
    if n >= 1_000_000:
        return f"GHS {n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"GHS {n/1_000:.1f}K"
    return f"GHS {n:.0f}"


def _html_report(result: dict[str, Any]) -> str:
    s = result["summary"]
    seg = result["segments"]

    cards = "".join(
        f"<div class='card'><div class='n'>{v}</div><div class='l'>{k}</div></div>"
        for k, v in [
            ("Total contacts", f"{s['total_contacts']:,}"),
            ("Valid mobile", f"{s['valid_contacts']:,}"),
            ("Businesses", f"{s['businesses']:,}"),
            ("Hot + warm", f"{s['hot'] + s['warm']}"),
            ("Diaspora", f"{s['diaspora']:,}"),
            ("With email", f"{s['emails']:,}"),
            ("Projected revenue", _fmt_g(s['est_total_revenue'])),
            ("B2B clients", f"{s['channels']['b2b']['clients']}"),
        ]
    )

    act_rows = ""
    for act in ("hot", "warm", "recent", "cold"):
        a = seg["by_activity"].get(act)
        if not a:
            continue
        act_rows += (f"<tr><td><b>{act.title()}</b></td><td>{a['count']}</td>"
                     f"<td>{_fmt_g(a['best_revenue'])}</td><td>"
                     + ", ".join(f"{p['product']} ({p['count']})" for p in a["products"][:3])
                     + "</td></tr>")
    act_table = (f"<table><tr><th>Segment</th><th>Contacts</th><th>Best product</th>"
                 f"<th>Top offers</th></tr>{act_rows}</table>")

    vert_rows = ""
    for vid, v in sorted(seg["by_vertical"].items(),
                         key=lambda x: (-x[1]["count"])):
        vert_rows += (f"<tr><td><b>{v['name']}</b></td><td>{v['count']}</td>"
                      f"<td>{v['engaged']}</td><td>{_fmt_g(v['pipeline'])}</td>"
                      f"<td>{', '.join(x.replace('_',' ').title() for x in v['products'])}</td></tr>")
    vert_table = (f"<table><tr><th>Vertical</th><th>Contacts</th><th>Engaged</th>"
                  f"<th>Pipeline</th><th>Sell</th></tr>{vert_rows}</table>")

    country_rows = ""
    for cname, c in sorted(seg["by_country"].items(),
                           key=lambda x: -x[1]["count"]):
        country_rows += (f"<tr><td><b>{cname}</b></td><td>{c['count']}</td>"
                         f"<td>{c['businesses']}</td><td>{c['emails']}</td>"
                         f"<td>{c['with_website']}</td><td>{c['tier']}</td></tr>")
    country_table = (f"<table><tr><th>Country</th><th>Contacts</th><th>Businesses</th>"
                     f"<th>Emails</th><th>Websites</th><th>Tier</th></tr>{country_rows}</table>")

    pb_rows = ""
    for p in result["playbook"][:50]:
        badge = "biz" if p["is_business"] else ("dia" if p["diaspora"] else "per")
        pb_rows += (f"<tr><td>{p['rank']}</td><td>{p['name']}</td><td>{p['phone']}</td>"
                    f"<td><span class='bdg {badge}'>{p['activity']}</span></td>"
                    f"<td>{p['vertical']}</td><td>{p['value_score']:.2f}</td>"
                    f"<td>{p['email']}</td><td>{', '.join(p['sell'][:2])}</td></tr>")
    pb_table = (f"<table><tr><th>#</th><th>Name</th><th>Phone</th><th>Activity</th>"
                f"<th>Vertical</th><th>Score</th><th>Email</th><th>Sell</th></tr>{pb_rows}</table>")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>mywa Revenue Projection</title>
<style>
 body{{font-family:'Segoe UI',Arial,sans-serif;margin:2rem;color:#1f2937;background:#f9fafb}}
 h1{{color:#075E54}} h2{{color:#075E54;margin-top:2rem}}
 .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin:1rem 0}}
 .card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:1rem;box-shadow:0 1px 2px rgba(0,0,0,.05)}}
 .card .n{{font-size:1.5rem;font-weight:800;color:#075E54;display:block}}
 .card .l{{font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:#6b7280;font-weight:600}}
 table{{border-collapse:collapse;width:100%;background:#fff;margin-top:.5rem}}
 th,td{{text-align:left;padding:.5rem .75rem;border-bottom:1px solid #e5e7eb;font-size:.85rem}}
 th{{background:#075E54;color:#fff}} tr:nth-child(even){{background:#f3faf8}}
 .bdg{{display:inline-block;border-radius:999px;padding:.15rem .6rem;font-size:.72rem;font-weight:700;color:#fff}}
 .hot{{background:#b91c1c}}.warm{{background:#b45309}}.recent{{background:#1d4ed8}}.cold{{background:#64748b}}
 .biz{{background:#6d28d9}}.dia{{background:#be185d}}.per{{background:#047857}}
</style></head><body>
<h1>Revenue Projection</h1>
<div class="cards">{cards}</div>
<h2>By activity segment</h2>{act_table}
<h2>By vertical</h2>{vert_table}
<h2>By country</h2>{country_table}
<h2>Priority playbook (top 50)</h2>{pb_table}
</body></html>"""


def analyze(out_dir: str, output_dir: str = "revenue_out",
            currency: str = "GHS") -> dict[str, Any]:
    """Load contacts.json from out_dir and produce a revenue analysis."""
    path = os.path.join(out_dir, "contacts.json")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    agent = RevenueAgent(data.get("contacts", []), out_dir=output_dir,
                         currency=currency)
    result = agent.analyze()

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "revenue.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(output_dir, "revenue_report.html"), "w", encoding="utf-8") as fh:
        fh.write(_html_report(result))
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="mywa revenue",
                                 description="Project revenue from segmented contacts.")
    ap.add_argument("--out", "-o", nargs="+", default=["real_out"],
                    help="Pipeline output dir(s) containing contacts.json (default: real_out).")
    ap.add_argument("--output-dir", "-d", default="revenue_out",
                    help="Where to write revenue.json + revenue_report.html.")
    ap.add_argument("--currency", "-c", default="GHS")
    args = ap.parse_args(argv)

    merged: list[dict] = []
    for d in args.out:
        path = os.path.join(d, "contacts.json")
        with open(path, "r", encoding="utf-8") as fh:
            merged.extend(json.load(fh).get("contacts", []))
        print(f"loaded {path}")

    agent = RevenueAgent(merged, out_dir=args.output_dir, currency=args.currency)
    result = agent.analyze()

    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, "revenue.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(args.output_dir, "revenue_report.html"), "w", encoding="utf-8") as fh:
        fh.write(_html_report(result))

    s = result["summary"]
    print(f"\nRevenue projection for {s['total_contacts']:,} contacts ({args.currency}):")
    print(f"  B2B contracts    : {_fmt_g(s['channels']['b2b']['revenue'])} "
          f"({s['channels']['b2b']['clients']} clients, avg {_fmt_g(s['channels']['b2b']['avg_contract'])})")
    for t in s["channels"]["b2b"]["tiers"]:
        if t["clients"]:
            print(f"     {t['name']:10s} x{t['clients']:3d} = {_fmt_g(t['revenue'])}")
    print(f"  B2C campaigns    : {_fmt_g(s['channels']['b2c_campaigns']['revenue'])} "
          f"(reach {s['channels']['b2c_campaigns']['reach']})")
    print(f"  Diaspora         : {_fmt_g(s['channels']['diaspora']['revenue'])} "
          f"(reach {s['channels']['diaspora']['reach']})")
    print(f"  Product services : {_fmt_g(s['channels']['product_services']['revenue'])}")
    print(f"  TOTAL projected  : {_fmt_g(s['est_total_revenue'])}")
    print(f"Wrote {args.output_dir}/revenue.json + revenue_report.html")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

