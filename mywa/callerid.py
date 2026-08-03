"""Truecaller-lite: local reverse phone lookup built from the entire dataset.

Builds a name-by-number directory across all merged contacts, then resolves a
probable caller identity for any number that has no stored name. This is fully
local and private - it does not contact any external crowd-sourced service.
"""
from __future__ import annotations

from .models import SegmentedContact
from .normalizer import strip_plus


def build_directory(contacts) -> dict[str, str]:
    directory: dict[str, str] = {}
    for c in contacts:
        name = (c.name or "").strip()
        if not name:
            continue
        for number in c.numbers:
            digits = strip_plus(number)
            directory.setdefault(digits, name)
    return directory


def enrich(segmented: list[SegmentedContact], directory: dict[str, str]) -> list[SegmentedContact]:
    for s in segmented:
        if s.named:
            continue
        digits = strip_plus(s.e164)
        s.identifier = directory.get(digits, "")
    return segmented


def stats(segmented: list[SegmentedContact]) -> dict[str, int]:
    unnamed = [s for s in segmented if not s.named]
    identified = [s for s in unnamed if s.identifier]
    return {
        "unnamed": len(unnamed),
        "identified": len(identified),
        "unknown": len(unnamed) - len(identified),
    }