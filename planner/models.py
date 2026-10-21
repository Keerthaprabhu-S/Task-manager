from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Goal(models.Model):
    STATUS = [("active", "Active"), ("completed", "Completed"), ("paused", "Paused")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_date = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def progress(self):
        """Percent of linked tasks + milestones that are done."""
        tasks, milestones = self.tasks.all(), self.milestones.all()
        total = tasks.count() + milestones.count()
        done = tasks.filter(status="done").count() + milestones.filter(is_done=True).count()
        return {"percent": round(100 * done / total) if total else 0, "done": done, "total": total}

    def __str__(self):
        return self.title


class Milestone(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=200)
    due_date = models.DateField(null=True, blank=True)
    is_done = models.BooleanField(default=False)

    class Meta:
        ordering = ["is_done", "due_date", "id"]


class Task(models.Model):
    PRIORITY = [("low", "Low"), ("medium", "Medium"), ("high", "High")]
    STATUS = [("todo", "To do"), ("in_progress", "In progress"), ("done", "Done")]
    RECUR = [("none", "None"), ("daily", "Daily"), ("weekly", "Weekly"), ("custom", "Custom")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    goal = models.ForeignKey(Goal, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    priority = models.CharField(max_length=6, choices=PRIORITY, default="medium")
    category = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="todo")
    recurrence = models.CharField(max_length=6, choices=RECUR, default="none")
    recurrence_interval = models.PositiveIntegerField(null=True, blank=True)  # days, for "custom"
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "id"]

    def spawn_next(self):
        """Create the next occurrence of a recurring task."""
        days = {"daily": 1, "weekly": 7, "custom": self.recurrence_interval or 1}.get(self.recurrence)
        if not days:
            return None
        base = self.due_date or timezone.localdate()
        return Task.objects.create(
            user=self.user, goal=self.goal, title=self.title, description=self.description,
            due_date=base + timedelta(days=days), priority=self.priority, category=self.category,
            recurrence=self.recurrence, recurrence_interval=self.recurrence_interval)
