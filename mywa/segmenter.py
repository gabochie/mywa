"""Segmentation of extracted contacts into targeted opportunity groups."""
from __future__ import annotations

from datetime import datetime, timezone
from .models import Contact, SegmentedContact
from .normalizer import normalize, carrier_for, country_for, is_valid_mobile, strip_plus

ACTIVE_DAYS = 90

# Non-home-country E.164 country codes treated as the diaspora segment.
_DIASPORA = {"US", "GB", "ZA", "NG", "IN", "CN"}


def _is_diaspora(country: str) -> bool:
    return country in _DIASPORA


def _activity(contact: Contact, now: float) -> str:
    if contact.msg_count >= 50:
        return "hot"
    if contact.msg_count >= 10:
        return "warm"
    if contact.last_seen:
        age_days = (now - contact.last_seen) / 86400.0
        if age_days <= ACTIVE_DAYS:
            return "recent"
    return "cold"


def _origin(contact: Contact) -> str:
    has_groups = bool(contact.groups)
    has_dm = contact.msg_count > 0
    if has_groups and has_dm:
        return "direct_and_group"
    if has_groups:
        return "group_only"
    if has_dm:
        return "direct"
    if contact.source in ("vcf", "wa.db", "adb"):
        return "saved"
    return "derived"


def _group_tags(groups: list[str], opportunity_keywords: list[str]) -> list[str]:
    tags: list[str] = []
    lowered = [g.lower() for g in groups]
    for kw in opportunity_keywords:
        kwl = kw.lower()
        for i, g in enumerate(lowered):
            if kwl in g:
                if groups[i] not in tags:
                    tags.append(groups[i])
    return tags


def segment(contacts: list[Contact], country_code: str,
            opportunity_keywords: list[str] | None = None,
            now: float | None = None) -> list[SegmentedContact]:
    keywords = [k for k in (opportunity_keywords or []) if k]
    if now is None:
        now = datetime.now(timezone.utc).timestamp()
    out: list[SegmentedContact] = []
    for c in contacts:
        if not c.numbers and not c.emails and not c.name:
            continue
        if c.numbers:
            e164 = normalize(c.primary_number(), country_code)
        else:
            e164 = ""
        out.append(SegmentedContact(
            contact=c,
            e164=e164,
            country=country_for(e164),
            carrier=carrier_for(e164, country_code),
            valid=is_valid_mobile(e164, country_code),
            activity=_activity(c, now),
            origin=_origin(c),
            group_tags=_group_tags(c.groups, keywords),
            named=bool((c.name or "").strip()),
            diaspora=_is_diaspora(country_for(e164)),
        ))
    return out


def opportunities(segmented: list[SegmentedContact], keywords: list[str],
                  min_activity: str = "cold") -> list[SegmentedContact]:
    ranks = {"hot": 0, "warm": 1, "recent": 2, "cold": 3}
    out: list[SegmentedContact] = []
    for s in segmented:
        if not s.valid:
            continue
        matches = bool(keywords) and bool(s.group_tags)
        direct = s.origin in ("direct_and_group", "direct")
        if not matches and not direct:
            continue
        if ranks.get(s.activity, 3) > ranks.get(min_activity, 3):
            continue
        out.append(s)
    return out


def deduplicate(contacts: list[Contact], country_code: str) -> list[Contact]:
    buckets: list[Contact] = []
    by_num: dict[str, Contact] = {}
    by_email: dict[str, Contact] = {}
    by_name: dict[str, Contact] = {}
    for c in contacts:
        nums = [strip_plus(normalize(n, country_code)) for n in c.numbers]
        nums = [n for n in nums if n]
        emails = [e.strip().lower() for e in (c.emails or []) if e and e.strip()]
        name = (c.name or "").strip().lower()

        cand = None
        for n in nums:
            if n and n in by_num:
                cand = by_num[n]
                break
        if cand is None:
            for e in emails:
                if e and e in by_email:
                    cand = by_email[e]
                    break
        if cand is None and name and name in by_name:
            cand = by_name[name]

        if cand is not None:
            cand.merge(c)
            for n in nums:
                if n:
                    by_num[n] = cand
            for e in emails:
                by_email[e] = cand
            if name:
                by_name[name] = cand
        else:
            bucket = Contact(
                name=c.name, jid=c.jid, numbers=list(c.numbers),
                emails=list(c.emails), org=c.org, address=c.address,
                city=c.city, website=c.website, groups=list(c.groups),
                my_contact=c.my_contact, is_business=c.is_business,
                is_admin=c.is_admin, labels=c.labels,
                msg_count=c.msg_count, sent_count=c.sent_count,
                last_seen=c.last_seen, first_seen=c.first_seen,
                source=c.source,
            )
            buckets.append(bucket)
            for n in nums:
                if n:
                    by_num[n] = bucket
            for e in emails:
                by_email[e] = bucket
            if name:
                by_name[name] = bucket
    return buckets
