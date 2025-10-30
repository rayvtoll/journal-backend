from django.contrib import admin
from django.urls import path, include

from project.apps.core.views import (
    PositionListView,
    PositionWhatIfView,
    PositionWhatIfTogetherView,
    PositionWhatIfPerHourView,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("project.apps.core.urls")),
    path("", PositionListView.as_view(), name="positions_read_only"),
    path("what-if/", PositionWhatIfView.as_view(), name="positions_what_if"),
    path("what-if-together/", PositionWhatIfTogetherView.as_view(), name="positions_what_if_together"),
    path(
        "what-if-per-hour/",
        PositionWhatIfPerHourView.as_view(),
        name="positions_what_if_per_hour",
    ),
]
