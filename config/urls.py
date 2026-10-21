from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("api/auth/", include("accounts.urls")),
    path("api/", include("planner.urls")),
    path("", TemplateView.as_view(template_name="index.html")),  # SPA shell
]
