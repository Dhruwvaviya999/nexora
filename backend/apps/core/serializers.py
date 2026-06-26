"""Serializers documenting the dashboard response shape."""

from rest_framework import serializers

from apps.documents.serializers import DocumentSerializer
from apps.projects.serializers import ProjectSerializer
from apps.tasks.serializers import TaskSerializer


class DashboardStatsSerializer(serializers.Serializer):
    total_projects = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    archived_projects = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    total_documents = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    stats = DashboardStatsSerializer()
    recent_projects = ProjectSerializer(many=True)
    recent_tasks = TaskSerializer(many=True)
    recent_documents = DocumentSerializer(many=True)
