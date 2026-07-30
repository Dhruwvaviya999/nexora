from django.contrib import admin

from apps.handovers.models import Handover


@admin.register(Handover)
class HandoverAdmin(admin.ModelAdmin):
    list_display = ("task", "from_user", "to_user", "status", "reviewer", "created_at")
    list_filter = ("status",)
    search_fields = ("task__title", "summary")
