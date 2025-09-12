import matplotlib.pyplot as plt
import seaborn as sns

from django.db.models import QuerySet
from django_tables2 import SingleTableMixin
from django_filters.views import FilterView

from project.apps.core.filters import PositionFilterSet
from project.apps.core.models import Position
from project.apps.core.tables import PositionTable

from .helpers import COLOR_LIST, SNS_THEME, image_encoder, plotter


class PositionListView(SingleTableMixin, FilterView):
    """List view for positions with table and filter functionality."""

    template_name = "core/position_list.html"
    model = Position
    table_class = PositionTable
    filterset_class = PositionFilterSet

    def get_queryset(self):
        return super().get_queryset().filter(candles_before_entry=1).order_by("-start")

    @property
    def totals(self) -> dict:
        """Calculate totals for the positions."""

        return dict(
            len_positions=len(self.object_list),
            total_returns=sum(position.returns for position in self.object_list),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        plt.rcParams["axes.prop_cycle"] = plt.cycler(color=COLOR_LIST)
        sns.set_theme(**SNS_THEME)
        sns.set_context(
            "notebook",
            rc={
                "font.size": 6,
                "axes.titlesize": 12,
                "axes.labelsize": 10,
            },
        )

        object_list: QuerySet[Position] = self.object_list.order_by("start")

        # x as
        x_as_data = [str(i) for i in range(len(object_list))]

        # y as
        returns = []
        total_returns = 0
        for position in object_list:
            total_returns += position.returns
            returns.append(total_returns)
        y_as_data = [i for i in returns]

        # create plot
        fig, ax = plt.subplots()
        fig.set_size_inches(9, 4)

        # hide x-axis labels
        ax.get_xaxis().set_visible(False)

        # plots
        c = COLOR_LIST[-1]
        ax.plot(
            x_as_data, y_as_data, color=c, label="Returns", linewidth=3, markersize=8
        )
        ax.fill_between(x_as_data, 0, y_as_data, alpha=0.3, color=c)

        # add image to context
        context["img"] = image_encoder(plotter(plt))
        context["title"] = "Position overview"

        return context | self.totals