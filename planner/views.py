from collections import Counter
from datetime import timedelta

from django.db.models import Case, IntegerField, When
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Goal, Milestone, Task
from .serializers import GoalSerializer, MilestoneSerializer, TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD for the current user's tasks.
    Query params: view=today|upcoming|overdue, priority, status, category, goal, search, ordering."""
    serializer_class = TaskSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description", "category"]
    ordering_fields = ["due_date", "priority_rank", "created_at", "title"]
    ordering = ["due_date", "-priority_rank"]

    def get_queryset(self):
        q = self.request.query_params
        today = timezone.localdate()
        qs = Task.objects.filter(user=self.request.user).select_related("goal").annotate(
            priority_rank=Case(When(priority="high", then=3), When(priority="medium", then=2),
                               default=1, output_field=IntegerField()))
        view = q.get("view")
        if view == "today":
            qs = qs.filter(due_date=today)
        elif view == "upcoming":
            qs = qs.filter(due_date__gt=today).exclude(status="done")
        elif view == "overdue":
            qs = qs.filter(due_date__lt=today).exclude(status="done")
        for field in ("priority", "status", "goal"):
            if q.get(field):
                qs = qs.filter(**{field: q[field]})
        if q.get("category"):
            qs = qs.filter(category__iexact=q["category"])
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description", "category"]
    ordering_fields = ["target_date", "created_at", "title"]

    def get_queryset(self):
        qs = Goal.objects.filter(user=self.request.user).prefetch_related("milestones")
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MilestoneViewSet(viewsets.ModelViewSet):
    serializer_class = MilestoneSerializer

    def get_queryset(self):
        qs = Milestone.objects.filter(goal__user=self.request.user)
        if self.request.query_params.get("goal"):
            qs = qs.filter(goal_id=self.request.query_params["goal"])
        return qs


class DashboardView(APIView):
    def get(self, request):
        today = timezone.localdate()
        tasks = Task.objects.filter(user=request.user)
        since = timezone.now() - timedelta(days=400)
        days = Counter(timezone.localtime(d).date() for d in
                       tasks.filter(completed_at__gte=since).values_list("completed_at", flat=True))
        day = today if days[today] else today - timedelta(days=1)
        streak = 0
        while days[day]:
            streak += 1
            day -= timedelta(days=1)
        ctx = {"request": request}
        goals = Goal.objects.filter(user=request.user, status="active").prefetch_related("milestones")[:5]
        return Response({
            "today_tasks": TaskSerializer(tasks.filter(due_date=today), many=True, context=ctx).data,
            "overdue_count": tasks.filter(due_date__lt=today).exclude(status="done").count(),
            "active_goals": GoalSerializer(goals, many=True, context=ctx).data,
            "weekly": [{"date": (today - timedelta(days=i)).isoformat(), "count": days[today - timedelta(days=i)]}
                       for i in range(6, -1, -1)],
            "streak": streak,
        })


class RemindersView(APIView):
    """In-app reminders: open tasks that are due today or overdue."""
    def get(self, request):
        today = timezone.localdate()
        qs = Task.objects.filter(user=request.user, due_date__lte=today).exclude(status="done")[:50]
        return Response([{"id": t.id, "title": t.title, "due_date": t.due_date, "overdue": t.due_date < today}
                         for t in qs])
