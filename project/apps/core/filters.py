import django_filters

from project.apps.core.models import Position

class PositionFilterSet(django_filters.FilterSet):
    """FilterSet for the Position model."""

    week_day = django_filters.CharFilter(
        field_name="start__week_day", lookup_expr="exact", label="Week Day"
    )
    week_days = django_filters.NumericRangeFilter(
        field_name="start__week_day", lookup_expr="range", label="Week Days"
    )

    hour = django_filters.CharFilter(field_name="start__hour", lookup_expr="exact", label="Hour")
    hours = django_filters.NumericRangeFilter(
        field_name="start__hour", lookup_expr="range", label="Hours"
    )

    class Meta:
        model = Position
        fields = (
            "side",
            "start",
            "week_day",
            "week_days",
            "hour",
            "hours",
            "candles_before_entry",
            "liquidation_amount",
            "nr_of_liquidations",
        )
