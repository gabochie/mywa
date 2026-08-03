"""Parse WhatsApp per-chat "Export chat" text exports (zero-cost group extractor).

Per-chat exports reveal member phone numbers two ways:
  * the "created/added" event lines list every member (name + phone number)
  * message senders show a raw phone number whenever that member is not saved
    in the user's address book.

This produces one Contact per discovered number, tagged with the group name and
a per-number message count. Numbers are normalized to E.164 by the shared
normalizer; country/carrier/activity are assigned later by the segmenter.
"""
from __future__ import annotations

import os
import re
import zipfile

from ..models import Contact
from ..normalizer import normalize

_LINE = re.compile(r"^[\d]{1,2}/[\d]{1,2}/[\d]{2,4},\s*[\d]{1,2}:[\d]{2}(?:\s*[APap][Mm])?\s*-\s*(.*)$")
_GROUP = re.compile(r"created group(?:\s*\"([^\"]*)\")?", re.IGNORECASE)
_PHONE = re.compile(r"\+[0-9][0-9\s\-().]{5,}[0-9]")

_TITLE_PREFIX = re.compile(r"^(?:Chat|Message|WhatsApp Chat) (?:with|about)\s+", re.IGNORECASE)


def _digits(value: str) -> str:
    return re.sub(r"[\s\-().]", "", value or "")


def _e164_phone(match: re.Match) -> str:
    digits = _digits(match.group(0))
    if not digits.startswith("+"):
        digits = "+" + digits
    return normalize(digits)


def _title_from_path(path: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0]
    return _TITLE_PREFIX.sub("", name) or name


def parse_export(text: str, group_hint: str = "") -> list[Contact]:
    """Parse one chat-export text blob into Contact objects."""
    numbers: dict[str, dict[str, object]] = {}
    group = group_hint

    def ensure(e164: str) -> dict:
        if e164 not in numbers:
            numbers[e164] = {"label": "", "msgs": 0, "seen": False}
        return numbers[e164]

    for raw in text.splitlines():
        m = _LINE.match(raw)
        if not m:
            continue
        body = m.group(1)

        gt = _GROUP.search(body)
        if gt and gt.group(1):
            group = gt.group(1).strip().strip('"')

        lower = body.lower()
        if " added " in lower or " created " in lower or " added you" in lower:
            for item in re.split(r",\s*", body):
                ph = _PHONE.search(item)
                if not ph:
                    continue
                e164 = _e164_phone(ph)
                info = numbers.setdefault(e164, {"label": "", "msgs": 0, "number": False})
                label = item[: ph.start()].strip(" ,")
                if label and not info["label"]:
                    info["label"] = label
            continue

        sep = body.find(": ")
        if sep < 0:
            continue
        sender = body[:sep].strip()
        ph = _PHONE.search(sender)
        if not ph:
            continue
        e164 = _e164_phone(ph)
        info = numbers.setdefault(e164, {"label": "", "msgs": 0, "number": False})
        info["msgs"] = int(info["msgs"]) + 1
        info["number"] = True

    contacts: list[Contact] = []
    for e164, info in numbers.items():
        c = Contact(name=str(info["label"] or ""), source="whatsapp_export")
        c.numbers.append(e164)
        c.msg_count = int(info["msgs"])
        if group:
            c.groups.append(group)
        contacts.append(c)
    return contacts


def parse_export_txt(path: str) -> list[Contact]:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return parse_export(text, _title_from_path(path))


def parse_export_zip(path: str) -> list[Contact]:
    out: list[Contact] = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".txt"):
                continue
            hint = _title_from_path(name)
            with zf.open(name) as fh:
                text = fh.read().decode("utf-8", errors="replace")
            out.extend(parse_export(text, hint))
    return out