import base64
from datetime import timedelta
import io
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

from django.db.models import QuerySet
from django.utils import timezone
from django.views.generic.edit import FormView
from django_tables2 import SingleTableMixin
from django_filters.views import FilterView

from project.apps.core.filters import PositionFilterSet
from project.apps.core.forms import WhatIfForm
from project.apps.core.models import Position, OHLCV
from project.apps.core.tables import PositionTable, WhatIfPositionTable


COLOR_LIST = [
    "#47DBCD",
    "#F3A0F2",
    "#9D2EC5",
    "#661D98",
    "#F5B14C",
    "#2CBDFF",
]

INITIAL_CAPITAL = 10_000

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

        positions: QuerySet[Position] = Position.objects.filter(
            candles_before_entry=1,
        )
        if start_date_gte := form.cleaned_data["start_date_gte"]:
            positions = positions.filter(start__gte=start_date_gte)
        if start_date_lt := form.cleaned_data["start_date_lt"]:
            positions = positions.filter(start__lt=start_date_lt)
        if weekdays := form.cleaned_data["week_days"]:
            positions = positions.filter(start__week_day__in=weekdays)
        if hours := form.cleaned_data["hours"]:
            positions = positions.filter(start__hour__in=hours)
        if min_liq := form.cleaned_data.get("min_liquidation_amount"):
            positions = positions.filter(liquidation_amount__gte=min_liq)
        if max_liq := form.cleaned_data.get("max_liquidation_amount"):
            positions = positions.filter(liquidation_amount__lte=max_liq)
        if strategy_types := form.cleaned_data["strategy_types"]:
            positions = positions.filter(strategy_type__in=strategy_types)

        positions = positions.order_by("start")

        returns = []
        dates = []
        total_returns = INITIAL_CAPITAL
        wins = 0
        losses = 0
        tp: float = form.cleaned_data["tp"]
        sl_to_entry: float = form.cleaned_data["sl_to_entry"]
        use_tp1: bool = form.cleaned_data["use_tp1"]
        tp1: float = form.cleaned_data["tp1"]
        tp1_amount: float = form.cleaned_data["tp1_amount"]
        use_tp2: bool = form.cleaned_data["use_tp2"]
        tp2: float = form.cleaned_data["tp2"]
        tp2_amount: float = form.cleaned_data["tp2_amount"]
        use_reverse: bool = form.cleaned_data["use_reverse"]
        reverse_all: bool = form.cleaned_data["reverse_all"]
        no_overlap: bool = form.cleaned_data["no_overlap"]
        compound: bool = form.cleaned_data["compound"]
        last_long_candle_datetime = None
        last_short_candle_datetime = None

        object_list: list[Position] = []
        for position in positions:
            position.what_if_returns = 0
            sl: bool = form.cleaned_data["sl"]
            use_sl_to_entry: bool = form.cleaned_data["use_sl_to_entry"]
            if use_reverse:
                if reverse_all and position.strategy_type != "reversed":
                    position.side = "SHORT" if position.side == "LONG" else "LONG"
                
                elif not reverse_all and position.strategy_type == "reversed":
                    position.side = "SHORT" if position.side == "LONG" else "LONG"

            ohlcv_s = OHLCV.objects.filter(
                datetime__gte=position.start,
                datetime__lt=position.start + timezone.timedelta(days=28),
            ).order_by("datetime")
            tp1_finished = False
            tp2_finished = False
            if ohlcv_s.exists():
                position.entry_price = ohlcv_s.first().open
                position.amount = (
                    (total_returns if compound else INITIAL_CAPITAL)
                    / sl
                    / position.entry_price
                )
                amount = position.amount
                fees_for_opening = 100 * position.amount
                total_returns -= fees_for_opening
                position.what_if_returns -= fees_for_opening
            for candle in ohlcv_s:
                if position.side == "LONG":

                    # prevent overlapping trades if no_overlap is checked
                    if no_overlap:
                        if (
                            last_long_candle_datetime
                            and candle.datetime < last_long_candle_datetime
                        ):
                            break
                        last_long_candle_datetime = candle.datetime

                    # SL
                    if candle.low <= position.entry_price - (
                        position.entry_price * sl / 100
                    ):
                        total_returns -= (
                            100 * position.amount
                        )  # exchange fees for closing trade
                        position.closing_price = round(
                            position.entry_price - (position.entry_price * sl / 100), 1
                        )
                        loss = (position.entry_price * sl / 100) * amount
                        total_returns -= loss
                        position.what_if_returns -= loss
                        position.what_if_returns = (
                            f"$ {round(position.what_if_returns, 2):,}"
                        )
                        object_list.insert(0, position)
                        returns.append(total_returns)
                        dates.append(position.start)
                        losses += 1
                        break

                    # SL to entry
                    if use_sl_to_entry and candle.high > position.entry_price + (
                        position.entry_price * (sl_to_entry / 100 * tp / 100)
                    ):
                        sl = -sl
                        use_sl_to_entry = False  # only use once

                    # TP1
                    if use_tp1 and not tp1_finished:
                        if candle.close >= position.entry_price + (
                            position.entry_price * (tp1 / 100 * tp / 100)
                        ):
                            total_returns += (
                                position.entry_price * (tp * tp1 / 100) / 100
                            ) * (position.amount * tp1_amount / 100)
                            amount = amount - (position.amount * tp1_amount / 100)
                            tp1_finished = True

                    # TP2
                    if use_tp2 and not tp2_finished:
                        if candle.close >= position.entry_price + (
                            position.entry_price * (tp2 / 100 * tp / 100)
                        ):
                            total_returns += (
                                position.entry_price * (tp * tp2 / 100) / 100
                            ) * (position.amount * tp2_amount / 100)
                            amount = amount - (position.amount * tp2_amount / 100)
                            tp2_finished = True

                    # final TP
                    if candle.close >= position.entry_price + (
                        position.entry_price * tp / 100
                    ):
                        fees_for_closing = 30 * position.amount
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
                        position.closing_price = round(
                            position.entry_price + (position.entry_price * tp / 100), 1
                        )
                        local_win = (position.entry_price * tp / 100) * amount
                        total_returns += local_win
                        position.what_if_returns += local_win
                        position.what_if_returns = f"$ {round(position.what_if_returns, 2):,}"
                        object_list.insert(0, position)
                        returns.append(total_returns)
                        dates.append(position.start)
                        wins += 1
                        break

                if position.side == "SHORT":

                    # prevent overlapping trades if no_overlap is checked
                    if no_overlap:
                        if (
                            last_short_candle_datetime
                            and candle.datetime < last_short_candle_datetime
                        ):
                            break
                        last_short_candle_datetime = candle.datetime

                    # SL
                    if candle.high >= position.entry_price + (
                        position.entry_price * sl / 100
                    ):
                        fees_for_closing = 30 * position.amount
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
                        position.closing_price = round(
                            position.entry_price - (position.entry_price * sl / 100), 1
                        )
                        loss = (position.entry_price * sl / 100) * amount
                        total_returns -= loss
                        position.what_if_returns -= loss
                        position.what_if_returns = f"$ {round(position.what_if_returns, 2):,}"
                        position.liquidation_amount = loss
                        object_list.insert(0, position)
                        returns.append(total_returns)
                        dates.append(position.start)
                        losses += 1
                        break

                    # TP1
                    if use_tp1 and not tp1_finished:
                        if candle.close <= position.entry_price - (
                            position.entry_price * (tp1 / 100 * tp / 100)
                        ):
                            total_returns += (
                                position.entry_price * (tp * tp1 / 100) / 100
                            ) * (position.amount * tp1_amount / 100)
                            amount = amount - (position.amount * tp1_amount / 100)
                            tp1_finished = True

                    # TP2
                    if use_tp2 and not tp2_finished:
                        if candle.close <= position.entry_price - (
                            position.entry_price * (tp2 / 100 * tp / 100)
                        ):
                            total_returns += (
                                position.entry_price * (tp * tp2 / 100) / 100
                            ) * (position.amount * tp2_amount / 100)
                            amount = amount - (position.amount * tp2_amount / 100)
                            tp2_finished = True

                    # final TP
                    if candle.close <= position.entry_price - (
                        position.entry_price * tp / 100
                    ):
                        fees_for_closing = 30 * position.amount
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
                        position.closing_price = round(
                            position.entry_price + (position.entry_price * tp / 100), 1
                        )
                        local_wins = (position.entry_price * tp / 100) * amount
                        total_returns += local_wins
                        position.what_if_returns += local_wins
                        position.what_if_returns = f"$ {round(position.what_if_returns, 2):,}"
                        object_list.insert(0, position)
                        returns.append(total_returns)
                        dates.append(position.start)
                        wins += 1
                        break

        # y as
        y_as_data = [i for i in returns]

        # x as
        x_as_data = [str(i.date()) for i in dates]

        # Fill in missing dates with previous return value to avoid gaps in the plot
        date_range = []
        returns_filled = []
        current_date = dates[0].date()
        end_date = dates[-1].date()
        returns_dict = {d.date(): r for d, r in zip(dates, returns)}
        last_return = INITIAL_CAPITAL
        while current_date <= end_date:
            date_range.append(str(current_date))
            if current_date in returns_dict:
                last_return = returns_dict[current_date]
            returns_filled.append(last_return)
            current_date += timedelta(days=1)

        x_as_data = date_range
        y_as_data = returns_filled

        # create plot
        fig, ax = plt.subplots()
        fig.set_size_inches(9, 4)

        # hide x-axis labels
        plt.setp(ax.get_xticklabels(), rotation=45)

        # plots
        c = COLOR_LIST[-1]
        ax.plot(
            x_as_data, y_as_data, color=c, label="Capital", linewidth=2, markersize=8
        )
        ax.fill_between(x_as_data, 0, y_as_data, alpha=0.3, color=c)
        ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
        ax.set_ylim(bottom=min(y_as_data) if y_as_data else 0)

        # Show only every Nth date label to avoid clutter
        N = max(1, len(x_as_data) // 20)
        ax.set_xticks([x_as_data[i] for i in range(0, len(x_as_data), N)])

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
                table=WhatIfPositionTable(object_list),
            )
        )
