from django.apps import AppConfig


class MentionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mentions"
    verbose_name = "Mentions"

    def ready(self):
        # Connect the comment post_save receiver that syncs mentions.
        from apps.mentions import handlers  # noqa: F401
