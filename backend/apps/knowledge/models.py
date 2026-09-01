from django.db import models


class KnowledgeDocument(models.Model):
    """
    One durable, approved knowledge document available to the RAG
    layer.

    Identity for controlled (re-)ingestion is
    ``(source_type, source_reference)``: re-ingesting the same
    identity updates this row in place and fully rebuilds its
    chunks, so repeated ingestion never creates duplicates.

    ORM access to this model MUST go through
    apps/knowledge/services.py.
    """

    SOURCE_TYPE_CHOICES = [
        ("manual", "Manually entered"),
        ("internal_note", "Internal note"),
    ]

    title = models.CharField(
        max_length=255,
    )

    source_type = models.CharField(
        max_length=32,
        choices=SOURCE_TYPE_CHOICES,
        default="manual",
    )

    source_reference = models.CharField(
        max_length=255,
        help_text=(
            "Stable caller-controlled identity for this source. "
            "Re-ingesting the same value updates in place."
        ),
    )

    normalized_text = models.TextField()

    active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-updated_at",
            "-id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "source_type",
                    "source_reference",
                ],
                name="uniq_knowledge_source_identity",
            ),
        ]

    def __str__(self):
        return f"KnowledgeDocument {self.id} - {self.title}"


class KnowledgeChunk(models.Model):
    """
    One deterministic chunk of a KnowledgeDocument's normalized
    text. Chunks are always rebuilt as a set for their document;
    they are never edited individually.
    """

    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )

    chunk_index = models.PositiveIntegerField()

    content = models.TextField()

    metadata = models.JSONField(
        default=dict,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "document_id",
            "chunk_index",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "document",
                    "chunk_index",
                ],
                name="uniq_knowledge_chunk_index",
            ),
        ]

    def __str__(self):
        return (
            f"KnowledgeChunk doc={self.document_id} "
            f"#{self.chunk_index}"
        )
