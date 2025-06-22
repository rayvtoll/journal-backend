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
    week_days = django_filters.MultipleChoiceFilter(
        field_name="start__week_day",
        lookup_expr="exact",
        label="Week Days",
        choices=[
            (2, "Monday"),
            (3, "Tuesday"),
            (4, "Wednesday"),
            (5, "Thursday"),
            (6, "Friday"),
            (7, "Saturday"),
            (1, "Sunday"),
        ],
        initial=(2, 3, 4, 5, 6, 7),
    )

    hours = django_filters.MultipleChoiceFilter(
        field_name="start__hour",
        lookup_expr="exact",
        label="Hours",
        choices=[
            (0, "00:00"),
            (1, "01:00"),
            (2, "02:00"),
            (3, "03:00"),
            (4, "04:00"),
            (5, "05:00"),
            (6, "06:00"),
            (7, "07:00"),
            (8, "08:00"),
            (9, "09:00"),
            (10, "10:00"),
            (11, "11:00"),
            (12, "12:00"),
            (13, "13:00"),
            (14, "14:00"),
            (15, "15:00"),
            (16, "16:00"),
            (17, "17:00"),
            (18, "18:00"),
            (19, "19:00"),
            (20, "20:00"),
            (21, "21:00"),
            (22, "22:00"),
            (23, "23:00"),
        ],
        initial=(1, 2, 3, 4, 14, 15, 16, 17),
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
            "side",
            "start_date_gte",
            "start_date_lte",
            "week_days",
            "hours",
            "nr_of_liquidations",
            "min_liquidation_amount",
            "max_liquidation_amount",
        )
