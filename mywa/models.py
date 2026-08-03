"""Core data model shared across parsers, segmenter and exporters."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Contact:
    name: str = ""
    jid: str = ""
    numbers: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    org: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    website: str = ""
    my_contact: bool = False
    is_business: bool = False
    is_admin: bool = False
    labels: str = ""
    groups: list[str] = field(default_factory=list)
    msg_count: int = 0
    sent_count: int = 0
    last_seen: int = 0
    first_seen: int = 0
    source: str = "unknown"

    def primary_number(self) -> str:
        return self.numbers[0] if self.numbers else ""

    def merge(self, other: "Contact") -> None:
        for n in other.numbers:
            if n and n not in self.numbers:
                self.numbers.append(n)
        for e in other.emails:
            if e and e not in self.emails:
                self.emails.append(e)
        for g in other.groups:
            if g and g not in self.groups:
                self.groups.append(g)
        self.my_contact = self.my_contact or other.my_contact
        self.is_business = self.is_business or other.is_business
        self.is_admin = self.is_admin or other.is_admin
        if other.labels and other.labels not in self.labels:
            self.labels = other.labels
        if other.org and not self.org:
            self.org = other.org
        if other.address and not self.address:
            self.address = other.address
        if other.city and not self.city:
            self.city = other.city
        if other.country and not self.country:
            self.country = other.country
        if other.website and not self.website:
            self.website = other.website
        self.msg_count += other.msg_count
        self.sent_count += other.sent_count
        if other.last_seen > self.last_seen:
            self.last_seen = other.last_seen
        if other.first_seen and (not self.first_seen or other.first_seen < self.first_seen):
            self.first_seen = other.first_seen
        if other.name and not self.name:
            self.name = other.name
        if other.jid and not self.jid:
            self.jid = other.jid
        if other.source != "unknown":
            self.source = other.source

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SegmentedContact:
    contact: Contact
    e164: str
    country: str
    carrier: str
    valid: bool
    activity: str
    origin: str
    group_tags: list[str]
    named: bool = False
    identifier: str = ""
    diaspora: bool = False
    line: str = ""
    lookup: str = ""
    lookup_src: str = ""

    def row(self) -> dict:
        c = self.contact
        return {
            "name": c.name,
            "phone": self.e164,
            "country": self.country,
            "carrier": self.carrier,
            "valid": self.valid,
            "activity": self.activity,
            "origin": self.origin,
            "named": self.named,
            "caller": self.identifier,
            "diaspora": self.diaspora,
            "lookup": self.lookup,
            "lookup_src": self.lookup_src,
            "line": self.line,
            "org": c.org,
            "email": "; ".join(c.emails),
            "address": c.address,
            "city": c.city,
            "home_country": c.country,
            "website": c.website,
            "groups": "; ".join(c.groups),
            "group_tags": "; ".join(self.group_tags),
            "my_contact": c.my_contact,
            "is_business": c.is_business,
            "is_admin": c.is_admin,
            "labels": c.labels,
            "msg_count": c.msg_count,
            "sent_count": c.sent_count,
            "last_seen": self._ts(c.last_seen),
            "source": c.source,
        }

    @staticmethod
    def _ts(value: int) -> str:
        if not value:
            return ""
        return __import__("datetime").datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
