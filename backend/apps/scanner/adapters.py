"""
Source adapters for the lead scanner.

An adapter turns a source config into a list of *raw candidate
dicts*. Adapters do NOT normalize, score, deduplicate, persist, or
touch the CRM. They must not access the Django ORM.

Phase 4 v1 ships two offline adapters:

- ``manual``  : a structured in-memory feed (list of dicts)
- ``csv``     : a CSV string/file with a documented column set

Live third-party scraping (LinkedIn, Reddit, OnlineJobs, …) is
deliberately out of scope for v1 - see docs. New adapters can be
registered here later without changing the pipeline.
"""

import csv
import io


class SourceAdapterError(Exception):
    """Raised when a source cannot be read at all (bad config/format)."""


# CSV columns -> raw candidate keys. Extra columns are ignored;
# missing optional columns default to "".
CSV_COLUMN_MAP = {
    "company": "company_name",
    "company name": "company_name",
    "contact": "contact_name",
    "contact person": "contact_name",
    "job title": "opportunity_title",
    "opportunity": "opportunity_title",
    "title": "opportunity_title",
    "source": "source",
    "source link": "source_url",
    "source url": "source_url",
    "url": "source_url",
    "problem or opportunity": "description",
    "opportunity description": "description",
    "description": "description",
    "notes": "notes",
    "location": "location",
    "work arrangement": "work_arrangement",
    "remote": "work_arrangement",
    "compensation": "compensation_text",
    "salary": "compensation_text",
    "source id": "source_identifier",
    "source identifier": "source_identifier",
}


def _row_to_raw(row):
    raw = {}
    for key, value in row.items():
        if key is None:
            continue
        mapped = CSV_COLUMN_MAP.get(key.strip().lower())
        if mapped:
            raw[mapped] = (value or "").strip()
    return raw


class ManualFeedAdapter:
    """
    config = {"source": "manual", "items": [ {raw candidate}, ... ]}
    """

    name = "manual"

    def scan(self, config):
        items = config.get("items")
        if not isinstance(items, list):
            raise SourceAdapterError(
                "manual adapter requires config['items'] as a list."
            )
        results = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise SourceAdapterError(
                    f"manual item {index} is not an object."
                )
            raw = dict(item)
            raw.setdefault("source", config.get("source", "manual"))
            results.append(raw)
        return results


class CsvAdapter:
    """
    config = {"source": "csv", "content": "<csv text>"} or
             {"source": "csv", "path": "<file path>"}
    """

    name = "csv"

    def scan(self, config):
        content = config.get("content")
        if content is None:
            path = config.get("path")
            if not path:
                raise SourceAdapterError(
                    "csv adapter requires config['content'] or "
                    "config['path']."
                )
            try:
                with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                    content = fh.read()
            except OSError as exc:
                raise SourceAdapterError(
                    f"csv file could not be read: {type(exc).__name__}"
                ) from exc

        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise SourceAdapterError("csv has no header row.")

        source = config.get("source", "csv")
        results = []
        for row in reader:
            raw = _row_to_raw(row)
            raw.setdefault("source", source)
            results.append(raw)
        return results


_ADAPTERS = {
    ManualFeedAdapter.name: ManualFeedAdapter,
    CsvAdapter.name: CsvAdapter,
}

SUPPORTED_SOURCES = tuple(sorted(_ADAPTERS))


def get_adapter(name):
    try:
        return _ADAPTERS[name]()
    except KeyError:
        raise SourceAdapterError(
            f"Unsupported source '{name}'. Supported: "
            f"{', '.join(SUPPORTED_SOURCES)}."
        )
