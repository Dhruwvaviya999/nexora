from django.apps import AppConfig


class ActivitiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.activities"
    verbose_name = "Activities"

    def ready(self):
        from apps.activities import handlers  # noqa: F401
