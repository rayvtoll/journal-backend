import base64
import io
import matplotlib.pyplot as plt
import seaborn as sns

from django_tables2 import SingleTableMixin, tables
from django_filters.views import FilterView
from django.db.models import QuerySet

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


class PositionListView(SingleTableMixin, FilterView):
    """List view for positions with table and filter functionality."""

    template_name = "core/position_list.html"
    model = Position
    table_class = PositionTable
    filterset_class = PositionFilterSet

    def get_queryset(self):
        return super().get_queryset().order_by("-start")

    @property
    def totals(self) -> dict:
        """Calculate totals for the positions."""

        return dict(
            len_positions=len(self.object_list),
            total_returns=sum(position.returns for position in self.object_list),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        CB91_Blue = "#2CBDFE"
        CB91_Green = "#47DBCD"
        CB91_Pink = "#F3A0F2"
        CB91_Purple = "#9D2EC5"
        CB91_Violet = "#661D98"
        CB91_Amber = "#F5B14C"

        color_list = [
            CB91_Violet,
            CB91_Pink,
            CB91_Purple,
            CB91_Green,
            CB91_Amber,
            CB91_Blue,
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
            str(position.start.strftime("%Y-%m-%d")) for position in object_list
        ]

        # y as
        returns = []
        total_returns = 0
        for position in object_list:
            total_returns += position.returns
            returns.append(total_returns)
        y_as_data = [i for i in returns]

        # figuur
        fig, ax = plt.subplots()
        fig.set_size_inches(9, 4)

        # labels
        ax.set_xticks(range(len(x_as_data)))
        ax.set_xticklabels(x_as_data)

        # Format x-axis dates for better readability
        plt.xticks(rotation=90, ha="right")

        # plots
        c = color_list.pop()
        ax.plot(
            x_as_data, y_as_data, color=c, label="Returns", linewidth=3, markersize=8
        )
        ax.fill_between(x_as_data, 0, y_as_data, alpha=0.3, color=c)

        # bewerkingen
        context["img"] = _image_encoder(_plotter(plt))

        return context | self.totals
