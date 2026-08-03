"""Parse tab-separated dumps produced by the adb_extract helper script."""
from __future__ import annotations

from ..models import Contact


def parse_adb_tsv(path: str) -> list[Contact]:
    contacts: list[Contact] = []
    seen: dict[str, Contact] = {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            name = parts[0].strip()
            number = parts[1].strip() if len(parts) > 1 else ""
            if not number:
                continue
            if number not in seen:
                seen[number] = Contact(name=name, source="adb")
                contacts.append(seen[number])
            else:
                c = seen[number]
                if name and not c.name:
                    c.name = name
            c = seen[number]
            if number not in c.numbers:
                c.numbers.append(number)
    return contacts
