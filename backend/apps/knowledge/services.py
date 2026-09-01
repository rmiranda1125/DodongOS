"""
Knowledge service layer.

This is the ONLY place (with models.py) allowed to touch the
knowledge ORM. RAG / retrieval / chunking / AI orchestration and
views all go through these functions.

Ingestion is controlled: callers supply a small approved
``source_type`` plus a stable ``source_reference`` identity, and
re-ingesting the same identity updates the document in place and
fully rebuilds its chunks (no duplicate documents or chunks).
"""

from django.conf import settings
from django.db import transaction

from apps.knowledge import chunking
from apps.knowledge import retrieval
from apps.knowledge.models import KnowledgeChunk, KnowledgeDocument


APPROVED_SOURCE_TYPES = {
    "manual",
    "internal_note",
}


class KnowledgeIngestionError(Exception):
    """Raised when an ingestion request is invalid or unsafe."""


def _chunk_settings():
    return (
        settings.RAG_CHUNK_SIZE,
        settings.RAG_CHUNK_OVERLAP,
    )


def rebuild_chunks(*, document):
    """
    Delete and recreate all chunks for ``document`` from its
    current ``normalized_text``. Deterministic and idempotent.
    """

    chunk_size, overlap = _chunk_settings()

    pieces = chunking.chunk_text(
        document.normalized_text,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    with transaction.atomic():
        document.chunks.all().delete()

        KnowledgeChunk.objects.bulk_create(
            [
                KnowledgeChunk(
                    document=document,
                    chunk_index=index,
                    content=piece,
                    metadata={
                        "document_id": document.id,
                        "document_title": document.title,
                        "source_type": document.source_type,
                        "source_reference": (
                            document.source_reference
                        ),
                        "chunk_index": index,
                    },
                )
                for index, piece in enumerate(pieces)
            ]
        )

    return document.chunks.count()


def ingest_document(
    *,
    title,
    source_reference,
    text,
    source_type="manual",
    active=True,
):
    """
    Create or update one approved knowledge document, then rebuild
    its chunks. Returns the KnowledgeDocument.

    Repeated calls with the same (source_type, source_reference)
    update in place - never a duplicate.
    """

    if source_type not in APPROVED_SOURCE_TYPES:
        raise KnowledgeIngestionError(
            f"source_type '{source_type}' is not approved."
        )

    if not isinstance(title, str) or not title.strip():
        raise KnowledgeIngestionError("title is required.")

    if (
        not isinstance(source_reference, str)
        or not source_reference.strip()
    ):
        raise KnowledgeIngestionError(
            "source_reference is required for controlled ingestion."
        )

    normalized = chunking.normalize_text(text or "")

    if not normalized:
        raise KnowledgeIngestionError(
            "Document text cannot be empty."
        )

    if len(normalized) > settings.KNOWLEDGE_DOC_MAX_CHARS:
        raise KnowledgeIngestionError(
            "Document exceeds the maximum size of "
            f"{settings.KNOWLEDGE_DOC_MAX_CHARS} characters."
        )

    if chunking.looks_like_secret(normalized):
        raise KnowledgeIngestionError(
            "Refusing to ingest content that looks like a "
            "credential or secret."
        )

    with transaction.atomic():
        document, _created = (
            KnowledgeDocument.objects.select_for_update()
            .get_or_create(
                source_type=source_type,
                source_reference=source_reference.strip(),
                defaults={
                    "title": title.strip(),
                    "normalized_text": normalized,
                    "active": active,
                },
            )
        )

        document.title = title.strip()
        document.normalized_text = normalized
        document.active = active
        document.save(
            update_fields=[
                "title",
                "normalized_text",
                "active",
                "updated_at",
            ],
        )

        rebuild_chunks(document=document)

    return document


def reindex_document(*, document_id):
    """Rebuild chunks for one existing document by id."""

    document = KnowledgeDocument.objects.filter(
        id=document_id,
    ).first()

    if document is None:
        raise KnowledgeIngestionError(
            f"KnowledgeDocument {document_id} was not found."
        )

    return rebuild_chunks(document=document)


def set_document_active(*, document_id, active):
    document = KnowledgeDocument.objects.filter(
        id=document_id,
    ).first()

    if document is None:
        raise KnowledgeIngestionError(
            f"KnowledgeDocument {document_id} was not found."
        )

    document.active = bool(active)
    document.save(update_fields=["active", "updated_at"])
    return document


def retrieve_knowledge(*, query, limit=None):
    """
    Deterministic, read-only knowledge retrieval.

    Returns JSON-safe evidence dicts (best first). Never invokes an
    AI provider. Only chunks of active documents are considered.
    """

    if not isinstance(query, str) or not query.strip():
        return {
            "success": False,
            "error": {
                "code": "INVALID_QUERY",
                "message": "A non-empty query is required.",
            },
        }

    if len(query) > settings.RAG_QUERY_MAX_CHARS:
        return {
            "success": False,
            "error": {
                "code": "QUERY_TOO_LONG",
                "message": (
                    "Query exceeds the maximum length of "
                    f"{settings.RAG_QUERY_MAX_CHARS} characters."
                ),
            },
        }

    if limit is None:
        limit = settings.RAG_RETRIEVAL_LIMIT

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
        or limit > 50
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be between 1 and 50.",
            },
        }

    rows = list(
        KnowledgeChunk.objects.filter(
            document__active=True,
        ).values(
            "id",
            "chunk_index",
            "content",
            "document_id",
            "document__title",
            "document__source_type",
            "document__source_reference",
        )
    )

    candidates = [
        {
            "chunk_id": row["id"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "document_id": row["document_id"],
            "document_title": row["document__title"],
            "source_type": row["document__source_type"],
            "source_reference": (
                row["document__source_reference"]
            ),
        }
        for row in rows
    ]

    ranked = retrieval.rank_chunks(
        query=query,
        chunks=candidates,
        limit=limit,
    )

    return {
        "success": True,
        "query": query.strip(),
        "result_count": len(ranked),
        "evidence": ranked,
    }


def get_documents(*, limit=100):
    """Return knowledge documents as JSON-safe dicts, newest first."""

    docs = KnowledgeDocument.objects.all()[: max(1, int(limit))]

    return [
        {
            "id": doc.id,
            "title": doc.title,
            "source_type": doc.source_type,
            "source_reference": doc.source_reference,
            "active": doc.active,
            "chunk_count": doc.chunks.count(),
            "updated_at": doc.updated_at,
        }
        for doc in docs
    ]
