from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ai.views import (
    AIConversationViewSet,
    AISettingsView,
    ChatView,
    GenerateTasksView,
    PromptTemplateViewSet,
    SearchHistoryViewSet,
    SearchView,
    SummarizeView,
)

app_name = "ai"

router = DefaultRouter()
router.register("conversations", AIConversationViewSet, basename="conversation")
router.register("search-history", SearchHistoryViewSet, basename="search-history")
router.register("prompt-templates", PromptTemplateViewSet, basename="prompt-template")

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("search/", SearchView.as_view(), name="search"),
    path("summarize/", SummarizeView.as_view(), name="summarize"),
    path("generate-tasks/", GenerateTasksView.as_view(), name="generate-tasks"),
    path("settings/", AISettingsView.as_view(), name="settings"),
    *router.urls,
]
