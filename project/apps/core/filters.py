import django_filters

from project.apps.core.models import Position

class PositionFilterSet(django_filters.FilterSet):
    """FilterSet for the Position model."""

    week_day = django_filters.CharFilter(
        field_name="start__week_day", lookup_expr="exact"
    )
    week_days = django_filters.NumericRangeFilter(
        field_name="start__week_day", lookup_expr="range"
    )

    hour = django_filters.CharFilter(field_name="start__hour", lookup_expr="exact")
    hours = django_filters.NumericRangeFilter(
        field_name="start__hour", lookup_expr="range"
    )

    class Meta:
        model = Position
        fields = "__all__"
