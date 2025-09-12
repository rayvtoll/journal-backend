from django_tables2 import tables, TemplateColumn

from project.apps.core.models import Position


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
                "class": "bg-light",
            },
        }


class WhatIfPositionTable(PositionTable):
    """What if position table"""

    liquidation_amount = None
    candles_before_entry = None
    nr_of_liquidations = None
    returns = None

    class Meta:
        model = Position
        fields = (
            "id",
            "start",
            "side",
            "what_if_returns",
            "entry_price",
            "closing_price",
        )
        attrs = {
            "class": "table table-hover",
            "th": {
                "class": "bg-light",
            },
        }


class WhatIfPerHourPositionTable(tables.Table):
    """What if position table"""

    hour = tables.Column(
        verbose_name="Hour of Day",
        attrs={
            "td": {
                "class": lambda record: (
                    "text-success"
                    if (
                        record["live_nr_of_r_s"] > 0 or record["reversed_nr_of_r_s"] > 0
                    )
                    else ""
                )
            }
        },
        orderable=False,
    )
    live_nr_of_trades = tables.Column(verbose_name="Live # Trades", orderable=False)
    live_ratio = tables.Column(verbose_name="Live Win Ratio", orderable=False)
    live_nr_of_r_s = tables.Column(
        verbose_name="Live # R's",
        attrs={
            "td": {
                "class": lambda record: (
                    "text-success" if record["live_nr_of_r_s"] > 0 else "text-danger"
                )
            }
        },
        orderable=False,
    )
    reversed_nr_of_trades = tables.Column(
        verbose_name="Reversed # Trades", orderable=False
    )
    reversed_ratio = tables.Column(verbose_name="Reversed Win Ratio", orderable=False)
    reversed_nr_of_r_s = tables.Column(
        verbose_name="Reversed # R's",
        attrs={
            "td": {
                "class": lambda record: (
                    "text-success"
                    if record["reversed_nr_of_r_s"] > 0
                    else "text-danger"
                )
            }
        },
        orderable=False,
    )

    class Meta:
        attrs = {
            "class": "table table-hover",
            "th": {
                "class": "bg-light",
            },
        }
