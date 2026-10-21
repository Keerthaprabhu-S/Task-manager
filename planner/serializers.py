from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework import serializers

from .models import Goal, Milestone, Task


def clean(value):
    """Strip HTML tags and surrounding whitespace from free text."""
    return strip_tags(value or "").strip()


class TaskSerializer(serializers.ModelSerializer):
    goal_title = serializers.CharField(source="goal.title", read_only=True, default=None)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ["id", "title", "description", "due_date", "priority", "category", "status", "goal",
                  "goal_title", "recurrence", "recurrence_interval", "completed_at", "created_at", "is_overdue"]
        read_only_fields = ["completed_at", "created_at"]

    def get_is_overdue(self, t):
        return bool(t.due_date and t.status != "done" and t.due_date < timezone.localdate())

    def validate_title(self, v):
        v = clean(v)
        if not v:
            raise serializers.ValidationError("Title is required.")
        return v

    def validate_description(self, v):
        return clean(v)

    def validate_category(self, v):
        return clean(v)

    def validate_goal(self, goal):
        if goal and goal.user_id != self.context["request"].user.id:
            raise serializers.ValidationError("Goal not found.")
        return goal

    def validate(self, attrs):
        rec = attrs.get("recurrence", getattr(self.instance, "recurrence", "none"))
        interval = attrs.get("recurrence_interval", getattr(self.instance, "recurrence_interval", None))
        if rec == "custom" and not interval:
            raise serializers.ValidationError({"recurrence_interval": "Required for custom recurrence."})
        return attrs

    def create(self, data):
        task = super().create(data)
        if task.status == "done":
            self._on_done(task)
        return task

    def update(self, task, data):
        was_done = task.status == "done"
        task = super().update(task, data)
        if task.status == "done" and not was_done:
            self._on_done(task)
        elif task.status != "done" and was_done:
            task.completed_at = None
            task.save(update_fields=["completed_at"])
        return task

    @staticmethod
    def _on_done(task):
        task.completed_at = timezone.now()
        task.save(update_fields=["completed_at"])
        task.spawn_next()


class MilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = ["id", "goal", "title", "due_date", "is_done"]

    def validate_title(self, v):
        v = clean(v)
        if not v:
            raise serializers.ValidationError("Title is required.")
        return v

    def validate_goal(self, goal):
        if goal.user_id != self.context["request"].user.id:
            raise serializers.ValidationError("Goal not found.")
        return goal


class GoalSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    milestones = MilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = Goal
        fields = ["id", "title", "description", "target_date", "category", "status", "progress",
                  "milestones", "created_at"]
        read_only_fields = ["created_at"]

    def get_progress(self, g):
        return g.progress()

    def validate_title(self, v):
        v = clean(v)
        if not v:
            raise serializers.ValidationError("Title is required.")
        return v

    def validate_description(self, v):
        return clean(v)

    def validate_category(self, v):
        return clean(v)
