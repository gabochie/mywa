"""Parse WhatsApp's legacy contact database (wa.db)."""
from __future__ import annotations

import os
import sqlite3
from ..models import Contact


def jid_to_number(jid: str) -> str:
    if not jid:
        return ""
    return jid.split("@", 1)[0]


def _connect(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{os.path.abspath(path)}?mode=ro", uri=True)


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [r[1] for r in rows]
    except sqlite3.Error:
        return []


def _load_group_subjects(conn: sqlite3.Connection) -> dict[str, str]:
    subjects: dict[str, str] = {}
    cols = _columns(conn, "wa_groups")
    if not cols:
        return subjects
    select = [c for c in ("jid", "subject") if c in cols]
    if len(select) != 2:
        return subjects
    try:
        for row in conn.execute(f"SELECT {', '.join(select)} FROM wa_groups"):
            if row[0] and row[1]:
                subjects[row[0]] = row[1]
    except sqlite3.Error:
        pass
    return subjects


def _load_participants(conn: sqlite3.Connection, contacts: dict[str, Contact],
                       subjects: dict[str, str]) -> None:
    cols = _columns(conn, "group_participants")
    if "group_jid" not in cols or "contact_jid" not in cols:
        return
    try:
        for row in conn.execute(
            "SELECT group_jid, contact_jid FROM group_participants"
        ):
            gnum = jid_to_number(row[0] or "")
            cnum = jid_to_number(row[1] or "")
            label = subjects.get(row[0] or "") or gnum
            if cnum in contacts and label:
                if label not in contacts[cnum].groups:
                    contacts[cnum].groups.append(label)
                if cnum not in contacts[cnum].numbers:
                    contacts[cnum].numbers.append(cnum)
    except sqlite3.Error:
        pass


def parse_wa_db(path: str) -> list[Contact]:
    contacts: dict[str, Contact] = {}
    conn = _connect(path)
    try:
        cols = _columns(conn, "wa_contacts")
        if not cols:
            return []
        select = [c for c in ("jid", "display_name", "wa_name", "phone") if c in cols]
        rows = conn.execute(f"SELECT {', '.join(select)} FROM wa_contacts").fetchall()
        for row in rows:
            jid = row[0] or ""
            number = jid_to_number(jid)
            if not number and "phone" in cols:
                number = row[cols.index("phone")] or ""
            if not number:
                continue
            if number not in contacts:
                contacts[number] = Contact(source="wa.db")
            c = contacts[number]
            c.jid = jid or c.jid
            if not c.name:
                if "display_name" in cols and row[cols.index("display_name")]:
                    c.name = row[cols.index("display_name")]
                elif "wa_name" in cols and row[cols.index("wa_name")]:
                    c.name = row[cols.index("wa_name")]
            if number not in c.numbers:
                c.numbers.append(number)
            if "phone" in cols and row[cols.index("phone")]:
                phone = row[cols.index("phone")]
                if phone != number and phone not in c.numbers:
                    c.numbers.append(phone)
        subjects = _load_group_subjects(conn)
        _load_participants(conn, contacts, subjects)
    finally:
        conn.close()
    return list(contacts.values())
