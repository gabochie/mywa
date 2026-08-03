"""Parse Google Contacts / Android exported CSV files.

Handles the standard Google Contacts CSV header format, e.g.
"First Name,Middle Name,Last Name,...,Phone 1 - Label,Phone 1 - Value,...
Email 1 - Label,Email 1 - Value,Organization Name,...".
"""
from __future__ import annotations

import csv
import re

from ..models import Contact

_PHONE_COL = re.compile(r"^Phone \d+ - Value$")
_EMAIL_COL = re.compile(r"^E-?mail \d+ - Value$")
_ORG_COL = "Organization Name"
_FIRST = "First Name"
_MIDDLE = "Middle Name"
_LAST = "Last Name"
_NAME = "Name"
_FILE_AS = "File As"
_NOTES = "Notes"
_ADDR_FORMATTED = "Address 1 - Formatted"
_ADDR_STREET = "Address 1 - Street"
_ADDR_CITY = "Address 1 - City"
_ADDR_COUNTRY = "Address 1 - Country"
_ADDR_REGION = "Address 1 - Region"
_ADDR_POSTAL = "Address 1 - Postal Code"
_WEBSITE = "Website 1 - Value"

_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_ADDR_NOTE_RE = re.compile(r"address\s*[:=]\s*(.+)", re.IGNORECASE)


def _join(*parts: str) -> str:
    parts = [p for p in parts if p]
    return ", ".join(parts) if parts else ""


def parse_csv_file(path: str) -> list[Contact]:
    contacts: list[Contact] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            c = Contact(source="google_csv")
            c.name = _display_name(row)
            c.org = (row.get(_ORG_COL) or "").strip()
            street = (row.get(_ADDR_STREET) or "").strip()
            city = (row.get(_ADDR_CITY) or "").strip()
            region = (row.get(_ADDR_REGION) or "").strip()
            cc = (row.get(_ADDR_COUNTRY) or "").strip()
            addr = (row.get(_ADDR_FORMATTED) or "").strip()
            c.address = addr or _join(street, city, region, row.get(_ADDR_POSTAL))
            c.city = city
            c.country = cc or region
            c.website = (row.get(_WEBSITE) or "").strip()
            notes = (row.get(_NOTES) or "").strip()
            if notes:
                m = _URL_RE.search(notes)
                if m and not c.website:
                    c.website = m.group(0).rstrip(".,;")
                am = _ADDR_NOTE_RE.search(notes)
                if am and not c.address:
                    c.address = am.group(1).splitlines()[0].strip()
            for key, value in row.items():
                if not key:
                    continue
                if _PHONE_COL.match(key.strip()):
                    v = (value or "").strip()
                    if v and v not in c.numbers:
                        c.numbers.append(v)
                elif _EMAIL_COL.match(key.strip()):
                    v = (value or "").strip()
                    if v and v not in c.emails:
                        c.emails.append(v)
            if c.name or c.numbers or c.emails:
                contacts.append(c)
    return contacts


def _display_name(row: dict) -> str:
    given = (row.get(_FIRST) or "").strip()
    middle = (row.get(_MIDDLE) or "").strip()
    family = (row.get(_LAST) or "").strip()
    name = " ".join(p for p in (given, middle, family) if p).strip()
    if not name:
        name = (row.get(_FILE_AS) or "").strip()
    return name