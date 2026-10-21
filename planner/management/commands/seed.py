from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from planner.models import Goal, Milestone, Task


class Command(BaseCommand):
    help = "Create demo user (demo / demo12345) with sample goals and tasks."

    def handle(self, *args, **opts):
        User = get_user_model()
        user, created = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
        if not created:
            self.stdout.write("Demo data already exists."); return
        user.set_password("demo12345"); user.save()
        t = timezone.localdate()
        g = Goal.objects.create(user=user, title="Crack SDE placements", category="career",
                                target_date=t + timedelta(days=90), description="Daily DSA + projects")
        Milestone.objects.create(goal=g, title="Finish 100 DSA problems", is_done=True)
        Milestone.objects.create(goal=g, title="Mock interview", due_date=t + timedelta(days=30))
        rows = [("Solve 2 DSA problems", 0, "high", "done", "daily"), ("Revise SQL joins", 0, "medium", "todo", "none"),
                ("Update resume", -2, "high", "todo", "none"), ("Read OS notes", 3, "low", "in_progress", "weekly")]
        for title, off, pri, st, rec in rows:
            task = Task.objects.create(user=user, goal=g, title=title, due_date=t + timedelta(days=off),
                                       priority=pri, status=st, recurrence=rec, category="study")
            if st == "done":
                task.completed_at = timezone.now(); task.save()
        self.stdout.write(self.style.SUCCESS("Seeded. Login: demo / demo12345"))
