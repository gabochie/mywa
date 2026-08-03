"""Hybrid phone-number enrichment (optional, opt-in, zero cost by default).

Sources tried in order for any number that has no local name:

  local    reverse lookup across your own data (zero cost, always available)
  opencnam caller name for US/CA (free)
  endpoint a self-hosted / bulk lookup API you provide (URL + optional key)

Design rules:
  * OFF unless --lookup is passed, so it costs nothing and works offline.
  * Results cached on disk so the provider is charged only once per number.
  * Rate-limited; unreachable/optional providers are skipped without error.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

from .models import SegmentedContact
from .normalizer import strip_plus


class Result:
    __slots__ = ("name", "line", "carrier", "source")

    def __init__(self, name="", line="", carrier="", source=""):
        self.name = name
        self.line = line
        self.carrier = carrier
        self.source = source

    def filled(self) -> bool:
        return bool(self.name or self.line or self.carrier)

    @staticmethod
    def from_dict(d: dict) -> "Result":
        d = d or {}
        return Result(d.get("name", ""), d.get("line", ""), d.get("carrier", ""), d.get("source", ""))


def _fetch(url: str, timeout: float = 6.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def opencnam(digits: str, _key: str = "") -> Result:
    url = f"https://rest.opencnam.com/v3/phone/{urllib.parse.quote(digits)}"
    try:
        data = json.loads(_fetch(url))
    except Exception:
        return Result()
    name = (data.get("name") or "").strip()
    return Result(name=name, source="opencnam") if name else Result()


def endpoint(digits: str, base: str, key: str) -> Result:
    sep = "&" if "?" in base else "?"
    url = f"{base}{sep}{urllib.parse.urlencode({'number': digits})}"
    if key:
        url += f"&key={urllib.parse.quote(key)}"
    try:
        payload = json.loads(_fetch(url))
    except Exception:
        return Result()
    def pick(*keys):
        for k in keys:
            v = payload.get(k)
            if v:
                return str(v).strip()
        return ""
    name = pick("name", "caller_name", "callerName")
    line = pick("line", "line_type", "lineType")
    carrier = pick("carrier", "carrier_name", "carrierName")
    if not (name or line or carrier):
        return Result()
    return Result(name=name, line=line, carrier=carrier, source="endpoint")


class Engine:
    def __init__(self, providers: list, cache_dir: str, delay: float = 0.1):
        self.providers = providers
        self.cache_dir = cache_dir
        self.delay = delay
        os.makedirs(cache_dir, exist_ok=True)

    def _path(self, digits: str) -> str:
        digest = hashlib.sha1(digits.encode()).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{digest}.json")

    def resolve(self, digits: str) -> Result:
        path = self._path(digits)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    return Result.from_dict(json.load(fh))
            except Exception:
                pass
        result = Result()
        for _tag, func in self.providers:
            try:
                got = func(digits)
            except Exception:
                got = Result()
            if self.delay:
                time.sleep(self.delay)
            if got.filled():
                result = got
                break
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"name": result.name, "line": result.line,
                           "carrier": result.carrier, "source": result.source}, fh)
        except OSError:
            pass
        return result


def make_providers(enabled: str, endpoint_url: str, key: str) -> list:
    items = [p.strip().lower() for p in (enabled or "").split(",") if p.strip()]
    out = []
    want_open = not items or "all" in items or "opencnam" in items
    want_endpoint = endpoint_url and ("all" in items or "endpoint" in items)
    if want_open:
        out.append(("opencnam", lambda n: opencnam(n)))
    if want_endpoint:
        out.append(("endpoint", lambda n: endpoint(n, endpoint_url, key or "")))
    return out


def run_lookups(segmented: list[SegmentedContact], local_directory: dict,
                enabled: str, endpoint_url: str, key: str, cache_dir: str,
                delay: float = 0.1) -> tuple[int, int]:
    providers = make_providers(enabled, endpoint_url, key)
    engine = Engine(providers, cache_dir, delay)
    looked = 0
    resolved = 0
    for s in segmented:
        if s.named:
            continue
        digits = strip_plus(s.e164)
        if not digits:
            continue
        local = local_directory.get(digits, "")
        s.lookup = local or s.identifier
        s.lookup_src = "local"
        if not s.lookup and providers:
            looked += 1
            r = engine.resolve(digits)
            if r.filled():
                s.lookup = r.name or ""
                s.lookup_src = r.source
                s.line = r.line
                resolved += 1
    return looked, resolved