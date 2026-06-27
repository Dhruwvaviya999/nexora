"""Comment routes, mounted under /api/v1/comments/."""

from rest_framework.routers import DefaultRouter

from apps.comments.views import CommentViewSet

app_name = "comments"

router = DefaultRouter()
router.register("", CommentViewSet, basename="comment")

urlpatterns = router.urls
