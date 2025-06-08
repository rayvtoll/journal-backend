from django_tables2 import tables, TemplateColumn

from project.apps.core.models import Position


class PositionTable(tables.Table):
    """Position tabel"""

    id = TemplateColumn(
        template_code="""<a href="{{ record.admin_url }}">{{ record.id }}</a>"""
    )

    class Meta:
        model = Position
        fields = (
            "id",
            "time_frame",
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
