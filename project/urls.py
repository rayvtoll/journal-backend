from django.contrib import admin
from django.urls import path, include

from project.apps.core.views import (
    PositionListView,
    PositionWhatIfView,
    PositionWhatIfPerHourByEntryView,
    PositionWhatIfPerHourByLiquidationView,
    PositionWhatIfRSIView,
    PositionWhatIfATRView,
)
from project.apps.core.views.what_if_algorithm import PositionWhatIfAlgorithmView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("project.apps.core.urls")),
    path("", PositionListView.as_view(), name="positions_read_only"),
    path("what-if/", PositionWhatIfView.as_view(), name="positions_what_if"),
    path("what-if-atr/", PositionWhatIfATRView.as_view(), name="positions_what_if_atr"),
    path(
        "what-if-algorithm/",
        PositionWhatIfAlgorithmView.as_view(),
        name="positions_what_if_algorithm",
    ),
    path("what-if-rsi/", PositionWhatIfRSIView.as_view(), name="positions_what_if_rsi"),
    path(
        "what-if-per-hour-by-entry/",
        PositionWhatIfPerHourByEntryView.as_view(),
        name="positions_what_if_per_hour_by_entry",
    ),
    path(
        "what-if-per-hour-by-liquidation/",
        PositionWhatIfPerHourByLiquidationView.as_view(),
        name="positions_what_if_per_hour_by_liquidation",
    ),
]
