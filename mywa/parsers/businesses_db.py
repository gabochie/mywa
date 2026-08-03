"""Parse the gadata SQLite businesses database (from the aiw project).

Expected table `businesses` (subset used):
  id, name, phone, email, website, address, category, segment,
  rating, country, region, ...
"""
from __future__ import annotations

import os
import sqlite3

from ..models import Contact


def parse_businesses_db(path: str) -> list[Contact]:
    contacts: list[Contact] = []
    conn = sqlite3.connect(f"file:{os.path.abspath(path)}?mode=ro", uri=True)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(businesses)")]
        if not cols:
            return []
        quoted = ", ".join(f'"{c}"' for c in cols)
        for rec in conn.execute(f"SELECT {quoted} FROM businesses"):
            row = dict(zip(cols, rec))
            name = (row.get("name") or "").strip()
            phone = (row.get("phone") or "").strip()
            email = (row.get("email") or "").strip()
            if not (name or phone or email):
                continue
            c = Contact(
                name=name,
                source="gadata",
                org=(row.get("category") or "").strip(),
                address=(row.get("address") or "").strip(),
                website=(row.get("website") or "").strip(),
                is_business=(row.get("segment") or "").strip().lower() == "business",
            )
            if phone:
                c.numbers.append(phone)
            if email:
                c.emails.append(email)
            category = (row.get("category") or "").strip()
            if category:
                c.groups.append(category)
            rating = row.get("rating")
            if rating not in (None, ""):
                c.labels = f"rating {rating}"
            contacts.append(c)
    finally:
        conn.close()
    return contacts
