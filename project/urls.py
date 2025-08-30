from django.contrib import admin
from django.urls import path, include

from project.apps.core.views import PositionListView, PositionWhatIfView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("project.apps.core.urls")),
    path("", PositionListView.as_view(), name="positions_read_only"),
    path("what-if/", PositionWhatIfView.as_view(), name="positions_what_if"),
]
