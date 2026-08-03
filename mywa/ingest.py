"""Input auto-detection and pipeline orchestration."""
from __future__ import annotations

import os
import re
import sqlite3

from .models import Contact
from .parsers.vcf_parser import parse_vcf_file
from .parsers.wa_db import parse_wa_db
from .parsers.msgstore import parse_msgstore
from .parsers.adb_tsv import parse_adb_tsv
from .parsers.csv_contacts import parse_csv_file
from .parsers.whatsapp_csv import parse_whatsapp_csv
from .parsers.whatsapp_export import parse_export_txt, parse_export_zip
from .parsers.businesses_db import parse_businesses_db


def _sqlite_tables(path: str) -> list[str]:
    try:
        conn = sqlite3.connect(f"file:{os.path.abspath(path)}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()
    except sqlite3.Error:
        return []


def _sniff_csv_kind(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            header = fh.readline(2000).lower()
    except OSError:
        return "google_csv"
    if "saved_name" in header or "public_name" in header or "is_my_contact" in header:
        return "whatsapp"
    if "first name" in header or "given name" in header or "phone" in header:
        return "google_csv"
    return "google_csv"


def _sniff_txt_kind(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(600)
    except OSError:
        return "unknown"
    low = head.lower()
    if "end-to-end encrypted" in low or "- " in low and ":" in low and "web.whatsapp" in low:
        return "wa_chat"
    if re.search(r"\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}", head):
        return "wa_chat"
    return "unknown"


def detect_kind(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".vcf":
        return "vcf"
    if ext == ".csv":
        return _sniff_csv_kind(path)
    if ext == ".txt":
        return _sniff_txt_kind(path)
    if ext == ".zip":
        return "wa_chat_zip"
    if ext == ".tsv":
        return "tsv"
    if ext == ".db":
        tables = _sqlite_tables(path)
        if "wa_contacts" in tables:
            return "wa.db"
        if "message" in tables or "messages" in tables or "chat" in tables:
            return "msgstore.db"
        if "businesses" in tables:
            return "gadata"
        return "sqlite"
    return "unknown"


def _walk_directory(path: str) -> list[str]:
    found: list[str] = []
    for root, _dirs, files in os.walk(path):
        for f in files:
            p = os.path.join(root, f)
            kind = detect_kind(p)
            if kind in ("vcf", "google_csv", "whatsapp", "wa_chat", "wa_chat_zip", "tsv", "wa.db", "msgstore.db", "gadata"):
                found.append(p)
    return found


def parse_path(path: str) -> list[Contact]:
    kind = detect_kind(path)
    if kind == "vcf":
        return parse_vcf_file(path)
    if kind == "google_csv":
        return parse_csv_file(path)
    if kind == "whatsapp":
        return parse_whatsapp_csv(path)
    if kind == "wa_chat":
        return parse_export_txt(path)
    if kind == "wa_chat_zip":
        return parse_export_zip(path)
    if kind == "tsv":
        return parse_adb_tsv(path)
    if kind == "wa.db":
        return parse_wa_db(path)
    if kind == "msgstore.db":
        return parse_msgstore(path)
    if kind == "gadata":
        return parse_businesses_db(path)
    return []


def ingest(paths: list[str]) -> list[Contact]:
    contacts: list[Contact] = []
    for p in paths:
        if os.path.isdir(p):
            for f in _walk_directory(p):
                contacts.extend(parse_path(f))
        elif os.path.isfile(p):
            contacts.extend(parse_path(p))
    return contacts
