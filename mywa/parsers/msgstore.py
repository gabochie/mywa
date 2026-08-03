"""Parse WhatsApp message database (msgstore.db) to recover every contact,
including group members, with activity statistics.

Handles both the legacy schema (messages / chat / group_participants) and the
modern schema (message / jid / chat). Schema differences are resolved by
inspecting available columns, so it is resilient across WhatsApp versions.
"""
from __future__ import annotations

import os
import sqlite3
from ..models import Contact
from .wa_db import jid_to_number

_SERVER = "s.whatsapp.net"
_GROUP_JID = "@g.us"


def _connect(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{os.path.abspath(path)}?mode=ro", uri=True)


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [r[1] for r in rows]
    except sqlite3.Error:
        return []


def _is_contact_jid(jid: str) -> bool:
    return bool(jid) and "@" in jid and "@g.us" not in jid and "@broadcast" not in jid


def _contact(key: str, contacts: dict[str, Contact]) -> Contact:
    if key not in contacts:
        contacts[key] = Contact(source="msgstore.db")
    return contacts[key]


def _load_group_subjects(conn: sqlite3.Connection) -> dict[str, str]:
    subjects: dict[str, str] = {}
    if "chat" not in _tables(conn):
        return subjects
    cols = _columns(conn, "chat")
    jcol = "chat_remote_jid" if "chat_remote_jid" in cols else "jid"
    scol = "subject" if "subject" in cols else None
    jcols = [jcol]
    if scol:
        jcols.append(scol)
    try:
        for row in conn.execute(f"SELECT {', '.join(jcols)} FROM chat"):
            jid = row[0] or ""
            if _GROUP_JID not in jid:
                continue
            label = row[1] if scol else None
            subjects[jid] = (label or "").strip() or jid.split("@", 1)[0]
    except sqlite3.Error:
        pass
    return subjects


def _load_participants(conn: sqlite3.Connection, contacts: dict[str, Contact],
                       subjects: dict[str, str]) -> None:
    tables = _tables(conn)
    if "group_participants" not in tables:
        return
    cols = _columns(conn, "group_participants")
    has_gjid = "group_jid" in cols
    has_contact = "contact_jid" in cols
    has_grow = "group_jid_row_id" in cols
    has_crow = "jid_row_id" in cols
    if not (has_gjid and has_contact):
        if has_grow and has_crow:
            jid_map: dict[int, str] = {}
            if "jid" in tables:
                try:
                    for row in conn.execute("SELECT _id, user, server FROM jid"):
                        if row[2] == _SERVER and row[1]:
                            jid_map[int(row[0])] = row[1]
                except sqlite3.Error:
                    pass
            chat_map: dict[int, str] = {}
            if "chat" in tables:
                try:
                    for row in conn.execute(
                        "SELECT _id, chat_remote_jid, subject FROM chat"
                    ):
                        if _GROUP_JID in (row[1] or ""):
                            chat_map[int(row[0])] = (row[2] or "").strip() or row[1]
                except sqlite3.Error:
                    pass
            try:
                for row in conn.execute("SELECT group_jid_row_id, jid_row_id FROM group_participants"):
                    gname = chat_map.get(int(row[0])) or ""
                    cnum = jid_map.get(int(row[1])) or ""
                    if cnum and gname:
                        c = _contact(cnum, contacts)
                        if gname not in c.groups:
                            c.groups.append(gname)
                        if cnum not in c.numbers:
                            c.numbers.append(cnum)
            except sqlite3.Error:
                pass
        return
    try:
            for row in conn.execute("SELECT group_jid, contact_jid FROM group_participants"):
                gname = subjects.get(row[0] or "") or jid_to_number(row[0] or "")
                cnum = jid_to_number(row[1] or "")
                if cnum and gname:
                    c = _contact(cnum, contacts)
                    if gname not in c.groups:
                        c.groups.append(gname)
                    if cnum not in c.numbers:
                        c.numbers.append(cnum)
    except sqlite3.Error:
        pass


def _aggregate_messages(conn: sqlite3.Connection, contacts: dict[str, Contact]) -> None:
    tables = _tables(conn)
    msg_table = "message" if "message" in tables else ("messages" if "messages" in tables else None)
    if not msg_table:
        return
    cols = _columns(conn, msg_table)
    jcol = "key_remote_jid" if "key_remote_jid" in cols else "remote_jid"
    if jcol not in cols:
        return
    fcol = "key_from_me" if "key_from_me" in cols else "from_me"
    has_from_me = fcol in cols
    tcol = "timestamp" if "timestamp" in cols else None
    select = [jcol]
    if has_from_me:
        select.append(fcol)
    if tcol:
        select.append(tcol)
    try:
        for row in conn.execute(f"SELECT {', '.join(select)} FROM {msg_table}"):
            jid = row[0] or ""
            if not _is_contact_jid(jid):
                continue
            c = _contact(jid_to_number(jid), contacts)
            c.msg_count += 1
            number = jid_to_number(jid)
            if number not in c.numbers:
                c.numbers.append(number)
            if has_from_me and row[1]:
                c.sent_count += 1
            if tcol and row[len(row) - 1]:
                ts = int(row[len(row) - 1])
                if not c.last_seen or ts > c.last_seen:
                    c.last_seen = ts
                if not c.first_seen or ts < c.first_seen:
                    c.first_seen = ts
    except sqlite3.Error:
        pass


def _load_jid_names(conn: sqlite3.Connection, contacts: dict[str, Contact]) -> None:
    if "jid" not in _tables(conn):
        return
    cols = _columns(conn, "jid")
    if "user" not in cols or "server" not in cols:
        return
    dcol = "display_name" if "display_name" in cols else None
    select = ["user", "server"]
    if dcol:
        select.append(dcol)
    try:
        for row in conn.execute(f"SELECT {', '.join(select)} FROM jid"):
            if row[1] != _SERVER or not row[0]:
                continue
            key = row[0]
            if key not in contacts:
                contacts[key] = Contact(source="msgstore.db")
            c = contacts[key]
            if not c.name and dcol and row[2]:
                c.name = row[2]
            if key not in c.numbers:
                c.numbers.append(key)
    except sqlite3.Error:
        pass


def parse_msgstore(path: str) -> list[Contact]:
    contacts: dict[str, Contact] = {}
    conn = _connect(path)
    conn.row_factory = sqlite3.Row
    try:
        subjects = _load_group_subjects(conn)
        _load_participants(conn, contacts, subjects)
        _aggregate_messages(conn, contacts)
        _load_jid_names(conn, contacts)
    finally:
        conn.close()
    return list(contacts.values())
