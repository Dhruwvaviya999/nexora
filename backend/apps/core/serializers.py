"""Serializers documenting the dashboard response shape."""

from rest_framework import serializers

from apps.documents.serializers import DocumentSerializer
from apps.handovers.serializers import HandoverSerializer
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
    my_tasks = serializers.IntegerField()
    pending_handovers = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    stats = DashboardStatsSerializer()
    recent_projects = ProjectSerializer(many=True)
    recent_tasks = TaskSerializer(many=True)
    recent_documents = DocumentSerializer(many=True)
    pending_handovers = HandoverSerializer(many=True)


class StatusCountSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class PriorityCountSerializer(serializers.Serializer):
    priority = serializers.CharField()
    count = serializers.IntegerField()


class WeeklyPointSerializer(serializers.Serializer):
    week_start = serializers.DateField()
    created = serializers.IntegerField()
    completed = serializers.IntegerField()


class WorkloadEntrySerializer(serializers.Serializer):
    user_id = serializers.CharField()
    name = serializers.CharField()
    count = serializers.IntegerField()


class HandoverStatsSerializer(serializers.Serializer):
    pending = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    avg_review_hours = serializers.FloatField(allow_null=True)


class AnalyticsSerializer(serializers.Serializer):
    task_status = StatusCountSerializer(many=True)
    task_priority = PriorityCountSerializer(many=True)
    weekly = WeeklyPointSerializer(many=True)
    workload = WorkloadEntrySerializer(many=True)
    handovers = HandoverStatsSerializer()
