from django_tables2 import SingleTableMixin, tables
from django_filters.views import FilterView

from project.apps.core.filters import PositionFilterSet
from project.apps.core.models import Position


class PositionTable(tables.Table):
    """Position tabel"""

    class Meta:
        model = Position
        fields = (
            "id",
            "start",
            "side",
            "take_profit_price",
            "stop_loss_price",
            "amount",
            "returns",
            "entry_price",
            "exit_price",
        )
        attrs = {
            "class": "table table-hover",
            "th": {
                "class": "bg-light",
            },
        }


class PositionListView(SingleTableMixin, FilterView):
    """List view for positions with table and filter functionality."""

    template_name = "core/position_list.html"
    model = Position
    table_class = PositionTable
    filterset_class = PositionFilterSet
    queryset = Position.objects.all().order_by("-start")

    def get_totals(self):
        """Calculate totals for the positions."""

        return dict(
            len_positions=len(self.object_list),
            total_returns=sum(position.returns for position in self.object_list),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = context | self.get_totals()
        return context
