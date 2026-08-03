"""Parse WhatsApp contact-dump CSV exports (e.g. from WhatsApp Exporter).

Expected columns (subset used):
  phone_number, formatted_phone, is_my_contact, saved_name, public_name,
  is_business, is_admin, labels, country_code
"""
from __future__ import annotations

import csv
import re

from ..models import Contact

_TRUE = re.compile(r"^(true|yes|1|y)$", re.IGNORECASE)


def _as_bool(value) -> bool:
    return bool(value) and isinstance(value, str) and bool(_TRUE.match(value.strip()))


def parse_whatsapp_csv(path: str) -> list[Contact]:
    contacts: list[Contact] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            phone = (row.get("phone_number") or row.get("formatted_phone") or "").strip()
            saved = (row.get("saved_name") or "").strip()
            public = (row.get("public_name") or "").strip()
            name = saved or public
            labels = (row.get("labels") or "").strip()
            c = Contact(
                name=name,
                source="whatsapp",
                my_contact=_as_bool(row.get("is_my_contact")),
                is_business=_as_bool(row.get("is_business")),
                is_admin=_as_bool(row.get("is_admin")),
                labels=labels,
            )
            if phone:
                c.numbers.append(phone)
            if c.numbers or c.name:
                contacts.append(c)
    return contacts