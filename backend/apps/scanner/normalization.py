"""
Deterministic normalization for scanner candidates.

Pure functions only: no ORM, no AI, no network, no randomness. The
same raw candidate always normalizes to the same output. Raw source
values are always preserved by the caller (stored in
``LeadCandidate.raw_data``); normalization never mutates the input.
"""

import re


_WS_RE = re.compile(r"\s+")
_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "ref",
    "referrer",
}
_COMPANY_SUFFIXES = (
    " inc",
    " inc.",
    " llc",
    " ltd",
    " ltd.",
    " limited",
    " corp",
    " corp.",
    " co",
    " co.",
    " gmbh",
    " pty",
    " plc",
)

REMOTE_TERMS = ("remote", "work from home", "wfh", "anywhere", "distributed")
HYBRID_TERMS = ("hybrid", "flexible")
ONSITE_TERMS = ("on-site", "onsite", "in office", "in-office", "on site")


def clean_text(value):
    if value is None:
        return ""
    return _WS_RE.sub(" ", str(value)).strip()


def normalize_company(value):
    cleaned = clean_text(value)
    lowered = cleaned.lower()
    for suffix in _COMPANY_SUFFIXES:
        if lowered.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].rstrip(" ,")
            break
    return cleaned


def normalize_title(value):
    return clean_text(value)


def normalize_location(value):
    return clean_text(value)


def normalize_url(value):
    """
    Canonicalize a URL for comparison: lowercase scheme+host, drop
    default ports, drop tracking query params, drop fragments and a
    trailing slash. Returns "" for anything that is not an http(s)
    URL.
    """

    cleaned = clean_text(value)
    if not cleaned:
        return ""

    match = re.match(
        r"^(https?)://([^/?#\s]+)([^?#\s]*)(?:\?([^#\s]*))?",
        cleaned,
        re.IGNORECASE,
    )
    if not match:
        return ""

    scheme = match.group(1).lower()
    host = match.group(2).lower()
    host = host.removeprefix("www.")
    host = re.sub(r":(80|443)$", "", host)
    path = match.group(3) or ""
    path = path.rstrip("/")

    query = match.group(4) or ""
    kept = []
    for part in query.split("&"):
        if not part:
            continue
        key = part.split("=", 1)[0].lower()
        if key in _TRACKING_PARAMS:
            continue
        kept.append(part)
    kept.sort()

    result = f"{scheme}://{host}{path}"
    if kept:
        result += "?" + "&".join(kept)
    return result


def normalize_work_arrangement(*, work_arrangement, title="", description=""):
    explicit = clean_text(work_arrangement).lower()
    haystack = " ".join(
        [explicit, clean_text(title).lower(), clean_text(description).lower()]
    )
    if any(term in haystack for term in REMOTE_TERMS):
        return "remote"
    if any(term in haystack for term in HYBRID_TERMS):
        return "hybrid"
    if any(term in haystack for term in ONSITE_TERMS):
        return "onsite"
    return explicit or "unknown"


def parse_compensation(value):
    """
    Best-effort deterministic parse of an annual figure from free
    text. Returns an int or None. "k" is treated as thousands;
    hourly rates (``/hr``, ``per hour``) are annualized at 2080h.
    """

    cleaned = clean_text(value).lower()
    if not cleaned:
        return None

    numbers = re.findall(r"\d[\d,]*(?:\.\d+)?\s*k?", cleaned)
    parsed = []
    for token in numbers:
        token = token.replace(",", "").strip()
        multiplier = 1
        if token.endswith("k"):
            multiplier = 1000
            token = token[:-1].strip()
        try:
            parsed.append(int(float(token) * multiplier))
        except ValueError:
            continue

    if not parsed:
        return None

    amount = max(parsed)
    if any(unit in cleaned for unit in ("/hr", "per hour", "hourly", "/hour")):
        amount *= 2080
    return amount


def normalize_candidate(raw):
    """
    Shape one raw candidate dict into normalized fields. ``raw`` is
    a plain dict from a source adapter; keys are best-effort.
    """

    company = normalize_company(raw.get("company_name"))
    title = normalize_title(
        raw.get("opportunity_title") or raw.get("job_title")
    )
    description = clean_text(raw.get("description"))
    source = clean_text(raw.get("source")).lower() or "manual"
    source_identifier = clean_text(raw.get("source_identifier"))
    source_url = normalize_url(raw.get("source_url"))
    location = normalize_location(raw.get("location"))
    work_arrangement = normalize_work_arrangement(
        work_arrangement=raw.get("work_arrangement", ""),
        title=title,
        description=description,
    )
    compensation_text = clean_text(raw.get("compensation_text"))

    return {
        "source": source,
        "source_identifier": source_identifier,
        "source_url": source_url,
        "company_name": company,
        "contact_name": clean_text(raw.get("contact_name")),
        "opportunity_title": title,
        "description": description,
        "location": location,
        "work_arrangement": work_arrangement,
        "compensation_text": compensation_text,
        "compensation_annual": parse_compensation(compensation_text),
        "search_text": " ".join([title, description]).strip().lower(),
    }
