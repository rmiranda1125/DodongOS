"""
Deterministic candidate deduplication keys.

Pure functions only - no ORM, no AI. AI is never the authoritative
duplicate detector.

Priority:
  1. exact source + source_identifier   -> "sid:<source>:<identifier>"
  2. canonical source URL               -> "url:<normalized-url>"
  3. fallback fingerprint over stable   -> "fp:<sha1(company|title|source)>"
     normalized fields
"""

import hashlib


def build_dedup_key(normalized):
    """
    ``normalized`` is the dict returned by
    normalization.normalize_candidate().
    """

    source = (normalized.get("source") or "manual").strip().lower()
    identifier = (normalized.get("source_identifier") or "").strip().lower()
    if identifier:
        return f"sid:{source}:{identifier}"

    url = (normalized.get("source_url") or "").strip().lower()
    if url:
        return f"url:{url}"

    company = (normalized.get("company_name") or "").strip().lower()
    title = (normalized.get("opportunity_title") or "").strip().lower()
    digest = hashlib.sha1(
        f"{company}|{title}|{source}".encode("utf-8")
    ).hexdigest()
    return f"fp:{digest}"
