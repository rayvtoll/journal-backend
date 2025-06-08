import django_filters

from project.apps.core.models import Position


class PositionFilterSet(django_filters.FilterSet):
    """FilterSet for the Position model."""

    start_date_gte = django_filters.DateTimeFilter(
        field_name="start__date",
        lookup_expr="gte",
        label="Min Start Date",
    )
    start_date_lte = django_filters.DateTimeFilter(
        field_name="start__date",
        lookup_expr="lte",
        label="Max Start Date",
    )
    week_days = django_filters.NumericRangeFilter(
        field_name="start__week_day", lookup_expr="range", label="Week Days"
    )

    hours = django_filters.NumericRangeFilter(
        field_name="start__hour", lookup_expr="range", label="Hours"
    )

    min_liquidation_amount = django_filters.NumberFilter(
        field_name="liquidation_amount",
        lookup_expr="gte",
        label="Min Liquidation",
    )
    max_liquidation_amount = django_filters.NumberFilter(
        field_name="liquidation_amount",
        lookup_expr="lte",
        label="Max Liquidation",
    )

    class Meta:
        model = Position
        fields = (
            "time_frame",
            "side",
            "start_date_gte",
            "start_date_lte",
            "week_days",
            "hours",
            "candles_before_entry",
            "nr_of_liquidations",
            "min_liquidation_amount",
            "max_liquidation_amount",
        )
