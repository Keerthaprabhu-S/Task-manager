from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("tasks", views.TaskViewSet, basename="task")
router.register("goals", views.GoalViewSet, basename="goal")
router.register("milestones", views.MilestoneViewSet, basename="milestone")

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view()),
    path("reminders/", views.RemindersView.as_view()),
    path("", include(router.urls)),
]
