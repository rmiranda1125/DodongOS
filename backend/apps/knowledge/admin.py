from django.contrib import admin

from apps.knowledge import services as knowledge_services
from apps.knowledge.models import KnowledgeChunk, KnowledgeDocument


class KnowledgeChunkInline(admin.TabularInline):
    model = KnowledgeChunk
    extra = 0
    can_delete = False
    fields = ("chunk_index", "content")
    readonly_fields = ("chunk_index", "content")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    """
    Staff knowledge management.

    Saving a document here rebuilds its chunks through the
    controlled service, so edits are always reindexed. A bulk
    "Reindex selected documents" action is also provided.
    """

    list_display = (
        "title",
        "source_type",
        "source_reference",
        "active",
        "updated_at",
    )
    list_filter = ("source_type", "active")
    search_fields = ("title", "source_reference", "normalized_text")
    ordering = ("-updated_at",)
    inlines = (KnowledgeChunkInline,)
    readonly_fields = ("created_at", "updated_at")
    actions = ("reindex_selected",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        knowledge_services.rebuild_chunks(document=obj)

    @admin.action(description="Reindex selected documents")
    def reindex_selected(self, request, queryset):
        count = 0
        for document in queryset:
            knowledge_services.reindex_document(
                document_id=document.id,
            )
            count += 1
        self.message_user(
            request,
            f"Reindexed {count} knowledge document(s).",
        )


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "chunk_index",
        "created_at",
    )
    list_filter = ("document__source_type",)
    search_fields = ("content", "document__title")
    ordering = ("document_id", "chunk_index")
    readonly_fields = (
        "document",
        "chunk_index",
        "content",
        "metadata",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
