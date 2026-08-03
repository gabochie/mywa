"""Parse standard .vcf (vCard 2.1 / 3.0) contact export files."""
from __future__ import annotations

import re
from ..models import Contact

_TEL_RE = re.compile(r"^TEL(?:;([^:]*))?:(.+)$")
_FN_RE = re.compile(r"^FN(?:;([^:]*))?:(.+)$")
_N_RE = re.compile(r"^N(?:;([^:]*))?:(.+)$")
_CONT = re.compile(r"^[ \t]")
_TELVAL = re.compile(r"[0-9+*#\-()./ ]")


def _unfold(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        line = line.rstrip("\r\n")
        if _CONT.match(line) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _tel_numbers(value: str) -> list[str]:
    parts = re.split(r"[;,]", value)
    nums: list[str] = []
    for part in parts:
        cleaned = "".join(_TELVAL.findall(part)).strip()
        if cleaned:
            nums.append(cleaned)
    return nums


def parse_vcf_text(text: str) -> list[Contact]:
    contacts: list[Contact] = []
    current: Contact | None = None
    for line in _unfold(text.splitlines()):
        if line.startswith("BEGIN:VCARD"):
            current = Contact(source="vcf")
        elif line.startswith("END:VCARD"):
            if current is not None:
                if current.numbers or current.name:
                    contacts.append(current)
                current = None
        elif current is None:
            continue
        else:
            m = _FN_RE.match(line)
            if m:
                current.name = m.group(2).strip()
                continue
            m = _N_RE.match(line)
            if m:
                parts = m.group(2).strip().split(";")
                if len(parts) >= 2 and not current.name:
                    family = parts[0].strip()
                    given = parts[1].strip()
                    if given:
                        current.name = f"{given} {family}".strip()
                continue
            m = _TEL_RE.match(line)
            if m:
                for n in _tel_numbers(m.group(2)):
                    if n not in current.numbers:
                        current.numbers.append(n)
    return contacts


def parse_vcf_file(path: str) -> list[Contact]:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return parse_vcf_text(fh.read())
