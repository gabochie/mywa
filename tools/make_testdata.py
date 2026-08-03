"""Generate synthetic WhatsApp data for testing mywa end-to-end."""
from __future__ import annotations

import os
import sqlite3
import time


def make_msgstore_modern(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE jid (_id INTEGER PRIMARY KEY, user TEXT, server TEXT, display_name TEXT);
    CREATE TABLE chat (_id INTEGER PRIMARY KEY, chat_remote_jid TEXT, subject TEXT);
    CREATE TABLE message (_id INTEGER PRIMARY KEY, key_remote_jid TEXT,
        key_from_me INTEGER, timestamp INTEGER, text_data TEXT);
    CREATE TABLE group_participants (group_jid TEXT, contact_jid TEXT);
    """)
    members = [
        ("233244111111", "Ama Boateng"),
        ("233244222222", "Kwame Mensah"),
        ("233245333333", "Efua Owusu"),
        ("233245444444", "Kofi Asante"),
        ("233246555555", "Yaa Darko"),
        ("233246666666", "Nana Addo"),
        ("233247777777", "Akosua Ankoma"),
        ("233248888888", "Kojo Anane"),
        ("233200999999", "Beatrice Tetteh"),
        ("233209887766", "Samuel Quaye"),
        ("233553456789", "Linda Acheampong"),
        ("233549876543", "Derrick Osei"),
    ]
    for i, (user, name) in enumerate(members):
        c.execute("INSERT INTO jid (_id, user, server, display_name) VALUES (?,?,?,?)",
                  (i + 1, user, "s.whatsapp.net", name))
    groups = [
        ("2331111111111@g.us", "Real Estate Investors Accra"),
        ("2332222222222@g.us", "Wholesale Distributors Network"),
        ("2333333333333@g.us", "Tech Founders Ghana"),
    ]
    for i, (gid, subj) in enumerate(groups):
        c.execute("INSERT INTO chat (_id, chat_remote_jid, subject) VALUES (?,?,?)",
                  (i + 1, gid, subj))
    c.execute("INSERT INTO chat (_id, chat_remote_jid, subject) VALUES (?,?,?)",
              (4, "233244111111@s.whatsapp.net", None))

    group_parts = [
        ("2331111111111@g.us", "233244111111@s.whatsapp.net"),
        ("2331111111111@g.us", "233244222222@s.whatsapp.net"),
        ("2331111111111@g.us", "233245333333@s.whatsapp.net"),
        ("2331111111111@g.us", "233245444444@s.whatsapp.net"),
        ("2332222222222@g.us", "233245333333@s.whatsapp.net"),
        ("2332222222222@g.us", "233245444444@s.whatsapp.net"),
        ("2332222222222@g.us", "233246555555@s.whatsapp.net"),
        ("2332222222222@g.us", "233246666666@s.whatsapp.net"),
        ("2333333333333@g.us", "233247777777@s.whatsapp.net"),
        ("2333333333333@g.us", "233248888888@s.whatsapp.net"),
        ("2333333333333@g.us", "233200999999@s.whatsapp.net"),
        ("2333333333333@g.us", "233553456789@s.whatsapp.net"),
        ("2333333333333@g.us", "233549876543@s.whatsapp.net"),
        ("2332222222222@g.us", "233209887766@s.whatsapp.net"),
    ]
    c.executemany("INSERT INTO group_participants VALUES (?,?)", group_parts)

    now = int(time.time())
    seed = 0
    for idx, (user, _name) in enumerate(members):
        for j in range(5 + (idx % 15)):
            seed += 1
            ts = now - (j + 1) * 3600
            c.execute("INSERT INTO message (key_remote_jid, key_from_me, timestamp, text_data) "
                      "VALUES (?,?,?,?)",
                      (f"{user}@s.whatsapp.net", seed % 3, ts, f"msg {seed}"))
    for j in range(120):
        seed += 1
        c.execute("INSERT INTO message (key_remote_jid, key_from_me, timestamp, text_data) "
                  "VALUES (?,?,?,?)",
                  ("233244111111@s.whatsapp.net", 1, now - j * 60, f"dm {seed}"))
    conn.commit()
    conn.close()


def make_msgstore_legacy(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE messages (_id INTEGER PRIMARY KEY, key_remote_jid TEXT,
        key_from_me INTEGER, timestamp INTEGER, text_data TEXT);
    CREATE TABLE chat (_id INTEGER PRIMARY KEY, chat_remote_jid TEXT, subject TEXT);
    CREATE TABLE jid (_id INTEGER PRIMARY KEY, user TEXT, server TEXT);
    CREATE TABLE group_participants (_id INTEGER PRIMARY KEY,
        group_jid_row_id INTEGER, jid_row_id INTEGER);
    """)
    users = [u for u, _ in [
        ("233244111111", "Ama Boateng"), ("233244222222", "Kwame Mensah"),
        ("233245333333", "Efua Owusu"), ("233245444444", "Kofi Asante"),
        ("233246555555", "Yaa Darko"), ("233200123456", "Old Friend"),
    ]]
    for i, u in enumerate(users):
        c.execute("INSERT INTO jid (_id, user, server) VALUES (?,?,?)",
                  (i + 1, u, "s.whatsapp.net"))
    for i, (gid, subj) in enumerate([
        ("2339999999999@g.us", "Family And Friends"),
    ]):
        c.execute("INSERT INTO chat (_id, chat_remote_jid, subject) VALUES (?,?,?)",
                  (i + 1, gid, subj))
    for gj, cj in [(1, 2), (1, 3), (1, 6)]:
        c.execute("INSERT INTO group_participants (group_jid_row_id, jid_row_id) VALUES (?,?)",
                  (gj, cj))
    now = int(time.time())
    for i in range(20):
        c.execute("INSERT INTO messages (key_remote_jid, key_from_me, timestamp, text_data) "
                  "VALUES (?,?,?,?)",
                  (f"{users[i % len(users)]}@s.whatsapp.net", i % 2, now - i * 100, "legacy"))
    conn.commit()
    conn.close()


def make_vcf(path: str) -> None:
    vcf = [
        "BEGIN:VCARD", "VERSION:3.0",
        "FN:Adwoa Nyarko", "N:Nyarko;Adwoa;;;",
        "TEL;TYPE=CELL:+233 24 987 6543",
        "TEL;TYPE=CELL:+233-24-123-4567",
        "END:VCARD",
        "BEGIN:VCARD", "VERSION:3.0",
        "FN:Kwabena Darko", "N:Darko;Kwabena;;;",
        "TEL;TYPE=CELL:0271 234 567",
        "END:VCARD",
        "BEGIN:VCARD", "VERSION:3.0",
        "FN:John Smith",
        "TEL;TYPE=CELL:+1 415 555 0132",
        "END:VCARD",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\r\n".join(vcf) + "\r\n")


def make_tsv(path: str) -> None:
    rows = [
        ("Maame Efua", "+233246000111"),
        ("Fiifi Acquah", "0553 222 333"),
        ("Adwoa Nyarko", "+233249876543"),
    ]
    with open(path, "w", encoding="utf-8") as fh:
        for name, num in rows:
            fh.write(f"{name}\t{num}\n")


def main() -> None:
    os.makedirs("testdata", exist_ok=True)
    make_msgstore_modern("testdata/msgstore.db")
    make_msgstore_legacy("testdata/legacy.db")
    make_vcf("testdata/contacts.vcf")
    make_tsv("testdata/adb_contacts.tsv")
    print("testdata generated")


if __name__ == "__main__":
    main()
