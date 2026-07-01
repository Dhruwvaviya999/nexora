from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.knowledge"
    verbose_name = "Knowledge (Embeddings & Retrieval)"

    def ready(self):
        # Wire the document -> embedding pipeline signal handlers.
        from apps.knowledge import handlers  # noqa: F401
