from django_tables2 import tables, TemplateColumn

from project.apps.core.models import Position


SUCCESS_TEXT = "text-success fw-bold"
MINIMUM_SUCCESS_PERCENTAGE = 22


class PositionTable(tables.Table):
    """Position tabel"""

    id = TemplateColumn(
        template_code="""<a href="{{ record.admin_url }}">{{ record.id }}</a>"""
    )
    returns = tables.Column(orderable=False)

    class Meta:
        model = Position
        fields = (
            "id",
            # "time_frame", # TODO: add time_frame field when more strategies are implemented
            "start",
            "side",
            "returns",
            "liquidation_amount",
            "candles_before_entry",
            "nr_of_liquidations",
            "entry_price",
            "closing_price",
        )
        attrs = {
            "class": "table table-hover",
            "th": {
                "class": "bg-dark",
            },
        }


class WhatIfPositionTable(PositionTable):
    """What if position table"""

    liquidation_amount = None
    nr_of_liquidations = None
    returns = None
    candles_before_entry = tables.Column(verbose_name="#Conf.")

    class Meta:
        model = Position
        fields = (
            "id",
            "candles_before_entry",
            "liquidation_datetime",
            "start",
            "side",
            "what_if_returns",
            "entry_price",
            "closing_price",
        )
        attrs = {
            "class": "table table-hover",
            "th": {
                "class": "bg-dark",
            },
        }


class WhatIfPerHourPositionTable(tables.Table):
    """What if position table"""

    hour = tables.Column(
        verbose_name="Hour of Day",
        attrs={
            "td": {
                "class": lambda record: (
                    SUCCESS_TEXT if (record["average_nr_of_r_s"] > 0) else ""
                )
            }
        },
        orderable=False,
    )
    average_ratio = tables.Column(
        verbose_name="Average Win %",
        attrs={
            "td": {
                "class": lambda record: (
                    SUCCESS_TEXT
                    if record["average_ratio"] > MINIMUM_SUCCESS_PERCENTAGE
                    else "text-secondary"
                )
            }
        },
        orderable=False,
    )
    average_nr_of_r_s = tables.Column(
        verbose_name="Average # R's",
        attrs={
            "td": {
                "class": lambda record: (
                    SUCCESS_TEXT
                    if record["average_nr_of_r_s"] > 0
                    else "text-secondary"
                )
            }
        },
        orderable=False,
    )
    total_nr_of_trades = tables.Column(verbose_name="Total # Trades", orderable=False)
    total_ratio = tables.Column(
        verbose_name="Total Win %",
        attrs={
            "td": {
                "class": lambda record: (
                    SUCCESS_TEXT
                    if record["total_ratio"] > MINIMUM_SUCCESS_PERCENTAGE
                    else "text-secondary"
                )
            }
        },
        orderable=False,
    )
    total_nr_of_r_s = tables.Column(
        verbose_name="Total # R's",
        attrs={
            "td": {
                "class": lambda record: (
                    SUCCESS_TEXT if record["total_nr_of_r_s"] > 0 else "text-secondary"
                )
            }
        },
        orderable=False,
    )
    six_month_nr_of_trades = tables.Column(
        verbose_name="6 Month # Trades", orderable=False
    )
    six_month_ratio = tables.Column(
        verbose_name="6 Month Win %",
        attrs={
            "td": {
                "class": lambda record: (
                    SUCCESS_TEXT
                    if record["six_month_ratio"] > MINIMUM_SUCCESS_PERCENTAGE
                    else "text-secondary"
                )
            }
        },
        orderable=False,
    )
    six_month_nr_of_r_s = tables.Column(
        verbose_name="6 Month # R's",
        attrs={
            "td": {
                "class": lambda record: (
                    SUCCESS_TEXT
                    if record["six_month_nr_of_r_s"] > 0
                    else "text-secondary"
                )
            }
        },
        orderable=False,
    )
    three_month_nr_of_trades = tables.Column(
        verbose_name="3 Month # Trades", orderable=False
    )
    three_month_ratio = tables.Column(
        verbose_name="3 Month Win %",
        attrs={
            "td": {
                "class": lambda record: (
                    "text-success"
                    if record["three_month_ratio"] > MINIMUM_SUCCESS_PERCENTAGE
                    else "text-secondary"
                )
            }
        },
        orderable=False,
    )
    three_month_nr_of_r_s = tables.Column(
        verbose_name="3 Month # R's",
        attrs={
            "td": {
                "class": lambda record: (
                    SUCCESS_TEXT
                    if record["three_month_nr_of_r_s"] > 0
                    else "text-secondary"
                )
            }
        },
        orderable=False,
    )

    class Meta:
        attrs = {
            "class": "table table-hover",
            "th": {
                "class": "bg-dark",
            },
        }
