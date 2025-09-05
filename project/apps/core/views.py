import base64
import io
import matplotlib.pyplot as plt
import seaborn as sns

from django.db.models import QuerySet
from django.utils import timezone
from django.views.generic.edit import FormView
from django_tables2 import SingleTableMixin
from django_filters.views import FilterView

from project.apps.core.filters import PositionFilterSet
from project.apps.core.forms import WhatIfForm
from project.apps.core.models import Position, OHLCV
from project.apps.core.tables import PositionTable


COLOR_LIST = [
    "#47DBCD",
    "#F3A0F2",
    "#9D2EC5",
    "#661D98",
    "#F5B14C",
    "#2CBDFF",
]

SNS_THEME = dict(
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


def plotter(plt: plt, legend: bool = True) -> io.BytesIO:
    """functie die een plot als een plaatje teruggeeft"""

    plt.grid(visible=True, which="major", axis="y", color="lightgrey", linestyle="--")
    if legend:
        plt.legend(frameon=False)
    s = io.BytesIO()
    plt.savefig(s, format="png", bbox_inches="tight")
    plt.close()
    return s


def image_encoder(s: io.BytesIO) -> str:
    """functie die plaatje als base64 verpakt zodat deze niet op de server hoeft te worden opgeslagen"""

    return base64.b64encode(s.getvalue()).decode("utf-8").replace("\n", "")


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

        return context | self.totals


class PositionWhatIfView(FormView):
    """List view for positions with table and filter functionality."""

    template_name = "core/what_if.html"
    model = Position
    table_class = PositionTable
    filterset_class = PositionFilterSet
    form_class = WhatIfForm

    def form_valid(self, form: WhatIfForm):
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

        object_list: QuerySet[Position] = Position.objects.filter(
            candles_before_entry=1,
        )
        if start_date_gte := form.cleaned_data["start_date_gte"]:
            object_list = object_list.filter(start__gte=start_date_gte)
        if start_date_lt := form.cleaned_data["start_date_lt"]:
            object_list = object_list.filter(start__lt=start_date_lt)
        if weekdays := form.cleaned_data["week_days"]:
            object_list = object_list.filter(start__week_day__in=weekdays)
        if hours := form.cleaned_data["hours"]:
            object_list = object_list.filter(start__hour__in=hours)
        if min_liq := form.cleaned_data.get("min_liquidation_amount"):
            object_list = object_list.filter(liquidation_amount__gte=min_liq)
        if max_liq := form.cleaned_data.get("max_liquidation_amount"):
            object_list = object_list.filter(liquidation_amount__lte=max_liq)
        if strategy_types := form.cleaned_data["strategy_types"]:
            object_list = object_list.filter(strategy_type__in=strategy_types)

        object_list = object_list.order_by("start")

        returns = []
        dates = []
        total_returns = 0
        wins = 0
        losses = 0
        sl = form.cleaned_data["sl"]
        tp = form.cleaned_data["tp"]
        use_tp1 = form.cleaned_data["use_tp1"]
        tp1 = form.cleaned_data["tp1"]
        tp1_amount = form.cleaned_data["tp1_amount"]
        use_tp2 = form.cleaned_data["use_tp2"]
        tp2 = form.cleaned_data["tp2"]
        tp2_amount = form.cleaned_data["tp2_amount"]
        reverse = form.cleaned_data["reverse"]
        no_overlap = form.cleaned_data["no_overlap"]
        last_long_candle_datetime = None
        last_short_candle_datetime = None

        for position in object_list:
            if reverse and position.strategy_type != "reversed":
                # do NOT save this to the database, just for the what-if analysis
                position.side = "SHORT" if position.side == "LONG" else "LONG"

            ohlcv_s = OHLCV.objects.filter(
                datetime__gte=position.start,
                datetime__lt=position.start + timezone.timedelta(days=15),
            ).order_by("datetime")
            tp1_finished = False
            tp2_finished = False
            amount = position.amount
            total_returns -= 0.007  # exchange fees for opening trade
            start = ohlcv_s.first().open if ohlcv_s.exists() else 0
            for candle in ohlcv_s:
                if position.side == "LONG":

                    # prevent overlapping trades if no_overlap is checked
                    if no_overlap:
                        if last_long_candle_datetime and candle.datetime < last_long_candle_datetime:
                            break
                        last_long_candle_datetime = candle.datetime

                    # SL
                    if candle.low <= start - (start * sl / 100):
                        total_returns -= 0.007  # exchange fees for closing trade
                        total_returns -= (start * sl / 100) * amount
                        returns.append(total_returns)
                        dates.append(position.start)
                        losses += 1
                        break

                    # TP1
                    if use_tp1 and not tp1_finished:
                        if candle.close >= start + (start * (tp1 / 100 * tp / 100)):
                            total_returns += (start * (tp * tp1 / 100) / 100) * (
                                position.amount * tp1_amount / 100
                            )
                            amount = amount - (position.amount * tp1_amount / 100)
                            tp1_finished = True

                    # TP2
                    if use_tp2 and not tp2_finished:
                        if candle.close >= start + (start * (tp2 / 100 * tp / 100)):
                            total_returns += (start * (tp * tp2 / 100) / 100) * (
                                position.amount * tp2_amount / 100
                            )
                            amount = amount - (position.amount * tp2_amount / 100)
                            tp2_finished = True

                    # final TP
                    if candle.close >= start + (start * tp / 100):
                        total_returns -= 0.002  # exchange fees for closing trade
                        total_returns += (start * tp / 100) * amount
                        returns.append(total_returns)
                        dates.append(position.start)
                        wins += 1
                        break

                if position.side == "SHORT":

                    # prevent overlapping trades if no_overlap is checked
                    if no_overlap:
                        if last_short_candle_datetime and candle.datetime < last_short_candle_datetime:
                            break
                        last_short_candle_datetime = candle.datetime

                    # SL
                    if candle.high >= start + (start * sl / 100):
                        total_returns -= 0.007  # exchange fees for closing trade
                        total_returns -= (start * sl / 100) * amount
                        returns.append(total_returns)
                        dates.append(position.start)
                        losses += 1
                        break

                    # TP1
                    if use_tp1 and not tp1_finished:
                        if candle.close <= start - (start * (tp1 / 100 * tp / 100)):
                            total_returns += (start * (tp * tp1 / 100) / 100) * (
                                position.amount * tp1_amount / 100
                            )
                            amount = amount - (position.amount * tp1_amount / 100)
                            tp1_finished = True

                    # TP2
                    if use_tp2 and not tp2_finished:
                        if candle.close <= start - (start * (tp2 / 100 * tp / 100)):
                            total_returns += (start * (tp * tp2 / 100) / 100) * (
                                position.amount * tp2_amount / 100
                            )
                            amount = amount - (position.amount * tp2_amount / 100)
                            tp2_finished = True

                    # final TP
                    if candle.close <= start - (start * tp / 100):
                        total_returns -= 0.002  # exchange fees for closing trade
                        total_returns += (start * tp / 100) * amount
                        returns.append(total_returns)
                        dates.append(position.start)
                        wins += 1
                        break

        y_as_data = [i for i in returns]

        # x as
        x_as_data = [str(i.date()) for i in dates]

        # create plot
        fig, ax = plt.subplots()
        fig.set_size_inches(9, 4)

        # hide x-axis labels
        plt.setp(ax.get_xticklabels(), rotation=45)

        # plots
        c = COLOR_LIST[-1]
        ax.plot(
            x_as_data, y_as_data, color=c, label="Returns", linewidth=3, markersize=8
        )
        ax.fill_between(x_as_data, 0, y_as_data, alpha=0.3, color=c)

        # add image to context
        img = image_encoder(plotter(plt))

        return self.render_to_response(
            self.get_context_data(
                img=img,
                form=form,
                ratio=(wins / (wins + losses)) if wins and losses else 0,
                wins=wins,
                losses=losses,
                nr_of_trades=wins + losses,
            )
        )
