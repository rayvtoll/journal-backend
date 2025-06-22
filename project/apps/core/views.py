import base64
import io
import matplotlib.pyplot as plt
import seaborn as sns

from django_tables2 import SingleTableMixin
from django_filters.views import FilterView
from django.db.models import QuerySet

from project.apps.core.filters import PositionFilterSet
from project.apps.core.models import Position
from project.apps.core.tables import PositionTable


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

        color_list = [
            "#47DBCD",
            "#F3A0F2",
            "#9D2EC5",
            "#661D98",
            "#F5B14C",
            "#2CBDFF",
        ]

        plt.rcParams["axes.prop_cycle"] = plt.cycler(color=color_list)

        sns.set_theme(
            font="DejaVu Sans",
            rc={
                "axes.axisbelow": False,
                "axes.edgecolor": "lightgrey",
                "axes.facecolor": "None",
                "axes.grid": False,
                "axes.labelcolor": "dimgrey",
                "axes.spines.right": False,
                "axes.spines.top": False,
                "figure.facecolor": "white",
                "lines.solid_capstyle": "round",
                "patch.edgecolor": "w",
                "patch.force_edgecolor": True,
                "text.color": "dimgrey",
                "xtick.bottom": False,
                "xtick.color": "dimgrey",
                "xtick.direction": "out",
                "xtick.top": False,
                "ytick.color": "dimgrey",
                "ytick.direction": "out",
                "ytick.left": False,
                "ytick.right": False,
            },
        )

        sns.set_context(
            "notebook",
            rc={
                "font.size": 6,
                "axes.titlesize": 12,
                "axes.labelsize": 10,
            },
        )

        def _plotter(plt: plt, legend: bool = True) -> io.BytesIO:
            """functie die een plot als een plaatje teruggeeft"""

            if legend:
                plt.legend(frameon=False)
            s = io.BytesIO()
            plt.savefig(s, format="png", bbox_inches="tight")
            plt.close()
            return s

        def _image_encoder(s: io.BytesIO) -> str:
            """functie die plaatje als base64 verpakt zodat deze niet op de server hoeft te worden opgeslagen"""

            return base64.b64encode(s.getvalue()).decode("utf-8").replace("\n", "")

        object_list: QuerySet[Position] = self.object_list.order_by("start")

        # x as
        x_as_data = [
            str(i) for i in range(len(object_list))
        ]

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
        c = color_list.pop()
        ax.plot(
            x_as_data, y_as_data, color=c, label="Returns", linewidth=3, markersize=8
        )
        ax.fill_between(x_as_data, 0, y_as_data, alpha=0.3, color=c)

        # add image to context
        context["img"] = _image_encoder(_plotter(plt))

        return context | self.totals
