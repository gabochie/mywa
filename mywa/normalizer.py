"""Phone number normalization to E.164 and Ghana carrier detection."""
from __future__ import annotations

import re

_DIGITS = re.compile(r"\D+")

CARRIER_PREFIXES = {
    "MTN": ["24", "25", "53", "54", "55", "59", "26"],
    "Telecel": ["20", "23", "50"],
    "AirtelTigo": ["27", "57"],
    "Expresso": ["28"],
    "Glo": ["37"],
}

DEFAULT_COUNTRY = "GH"

# Maps ISO alpha-2 country codes to E.164 dial codes. The pipeline passes dial
# codes (e.g. "233") as `country_code`; this table lets alpha-2 inputs ("GH")
# work too, so library-level default usage is always correct.
_ALPHA2_TO_DIAL = {
    "GH": "233", "NG": "234", "ZA": "27", "KE": "254",
    "TZ": "255", "UG": "256", "EG": "20", "MA": "212",
    "US": "1", "GB": "44", "IN": "91", "DE": "49", "FR": "33",
}


def _dial_code(country_code: str) -> str:
    """Normalize a country input (alpha-2 or E.164 dial code) to a dial code."""
    return _ALPHA2_TO_DIAL.get(country_code.upper(), country_code)


def _strip(value: str) -> str:
    return _DIGITS.sub("", value or "")


def _e164_core(value: str, country_code: str) -> str:
    digits = _strip(value)
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("+"):
        digits = digits[1:]
    if len(digits) == len(country_code) + 9 and digits.startswith(country_code):
        return digits
    if digits.startswith("0") and len(digits) == 10:
        return country_code + digits[1:]
    if len(digits) == 9:
        return country_code + digits
    if len(digits) == len(country_code) + 9:
        return digits
    return digits


def normalize(value: str, country_code: str = DEFAULT_COUNTRY) -> str:
    cc = _dial_code(country_code)
    core = _e164_core(value, cc)
    if len(core) == len(cc) + 9 and core.startswith(cc):
        return "+" + core
    if core and core[0] != "+":
        return "+" + core
    return core


def strip_plus(value: str) -> str:
    return _DIGITS.sub("", value or "")


def carrier_for(e164: str, country_code: str = DEFAULT_COUNTRY) -> str:
    cc = _dial_code(country_code)
    digits = strip_plus(e164)
    if not digits.startswith(cc) or len(digits) != len(cc) + 9:
        return ""
    pair = digits[len(cc):len(cc) + 2]
    for name, prefixes in CARRIER_PREFIXES.items():
        if pair in prefixes:
            return name
    return "Unknown"


def country_for(e164: str) -> str:
    digits = strip_plus(e164)
    if not digits:
        return ""
    if digits.startswith("233") and len(digits) == 12:
        return "GH"
    if digits.startswith("1") and len(digits) == 11:
        return "US"
    if digits.startswith("44") and len(digits) == 12:
        return "GB"
    if digits.startswith("27") and len(digits) == 11:
        return "ZA"
    if digits.startswith("234") and len(digits) == 13:
        return "NG"
    if digits.startswith("91") and len(digits) == 12:
        return "IN"
    if digits.startswith("86") and len(digits) == 12:
        return "CN"
    return "Other"


def is_valid_mobile(e164: str, country_code: str = DEFAULT_COUNTRY) -> bool:
    cc = _dial_code(country_code)
    digits = strip_plus(e164)
    return len(digits) == len(cc) + 9 and digits.startswith(cc)
