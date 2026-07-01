from django.contrib import admin

from apps.invitations.models import Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "workspace", "role", "status", "invited_by", "expires_at")
    list_filter = ("status", "role")
    search_fields = ("email", "workspace__name")
    readonly_fields = ("token", "created_at", "updated_at")
