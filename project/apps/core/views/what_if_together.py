import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

from django.db.models import QuerySet
from django.utils import timezone
from django.views.generic.edit import FormView

from project.apps.core.filters import PositionFilterSet
from project.apps.core.forms import WhatIfTogetherForm
from project.apps.core.models import Position, OHLCV
from project.apps.core.tables import WhatIfTogetherPositionTable

from .helpers import COLOR_LIST, INITIAL_CAPITAL, SNS_THEME, image_encoder, plotter


class PositionWhatIfTogetherView(FormView):
    """List view for positions with table and filter functionality."""

    template_name = "core/what_if.html"
    model = Position
    table_class = WhatIfTogetherPositionTable
    filterset_class = PositionFilterSet
    form_class = WhatIfTogetherForm

    def form_valid(self, form: WhatIfTogetherForm):
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

        positions: QuerySet[Position] = self.model.objects.filter(
            candles_before_entry=1,
        )
        if start_date_gte := form.cleaned_data["start_date_gte"]:
            positions = positions.filter(start__gte=start_date_gte)
        if start_date_lt := form.cleaned_data["start_date_lt"]:
            positions = positions.filter(start__lt=start_date_lt)

        positions = positions.order_by("start")

        returns = []
        dates = []
        total_returns = INITIAL_CAPITAL
        wins = 0
        losses = 0

        object_list: list[Position] = []
        for position in positions:

            position.what_if_returns = 0
            if (
                "live" in form.cleaned_data["strategies"]
                and str(position.start.weekday())
                in (form.cleaned_data["live_week_days"])
                and str(position.start.hour) in form.cleaned_data["live_hours"]
            ):
                if position.strategy_type == "reversed":
                    position.side = "SHORT" if position.side == "LONG" else "LONG"
                position.strategy_type = "live"
                sl: float = form.cleaned_data["live_sl"]
                tp: float = form.cleaned_data["live_tp"]
            elif (
                "reversed" in form.cleaned_data["strategies"]
                and str(position.start.weekday())
                in (form.cleaned_data["reversed_week_days"])
                and str(position.start.hour) in form.cleaned_data["reversed_hours"]
            ):
                if position.strategy_type != "reversed":
                    position.side = "SHORT" if position.side == "LONG" else "LONG"
                position.strategy_type = "reversed"
                sl: float = form.cleaned_data["reversed_sl"]
                tp: float = form.cleaned_data["reversed_tp"]
            elif (
                "grey" in form.cleaned_data["strategies"]
                and str(position.start.weekday())
                in (form.cleaned_data["grey_week_days"])
                and str(position.start.hour) in form.cleaned_data["grey_hours"]
            ):
                if position.strategy_type == "reversed":
                    position.side = "SHORT" if position.side == "LONG" else "LONG"
                position.strategy_type = "grey"
                sl: float = form.cleaned_data["grey_sl"]
                tp: float = form.cleaned_data["grey_tp"]
            else:
                continue  # skip position if no strategy matches

            iso_datetime = (
                f"{position.start.year}-"
                f"{position.start.month:02d}-"
                f"{position.start.day:02d} "
                f"{position.start.hour:02d}:{position.start.minute:02d}:00"
            )
            ohlcv_s = OHLCV.objects.filter(
                datetime__gte=timezone.datetime.fromisoformat(iso_datetime),
                datetime__lt=position.start + timezone.timedelta(days=28),
            ).order_by("datetime")
            if ohlcv_s.exists():
                position.entry_price = round(
                    (
                        ohlcv_s.first().open * 1.0001
                        if position.side == "SHORT"
                        else ohlcv_s.first().open * 0.9999
                    ),
                    1,
                )
                position.amount = total_returns / position.entry_price / sl
                amount = position.amount
                fees_for_opening = 100 * position.amount
                total_returns -= fees_for_opening
                position.what_if_returns -= fees_for_opening

            for candle in ohlcv_s:

                if position.side == "LONG":

                    # SL
                    if candle.low <= position.entry_price - (
                        position.entry_price * sl / 100
                    ):
                        fees_for_closing = 85 * position.amount
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
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
                        position.what_if_returns = (
                            f"$ {round(position.what_if_returns, 2):,}"
                        )
                        object_list.insert(0, position)
                        returns.append(total_returns)
                        dates.append(position.start)
                        wins += 1
                        break

                if position.side == "SHORT":

                    # SL
                    if candle.high >= position.entry_price + (
                        position.entry_price * sl / 100
                    ):
                        fees_for_closing = 85 * position.amount
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
                        position.closing_price = round(
                            position.entry_price + (position.entry_price * sl / 100), 1
                        )
                        loss = (position.entry_price * sl / 100) * amount
                        total_returns -= loss
                        position.what_if_returns -= loss
                        position.what_if_returns = (
                            f"$ {round(position.what_if_returns, 2):,}"
                        )
                        position.liquidation_amount = loss
                        object_list.insert(0, position)
                        returns.append(total_returns)
                        dates.append(position.start)
                        losses += 1
                        break

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
                        position.what_if_returns = (
                            f"$ {round(position.what_if_returns, 2):,}"
                        )
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
        current_date = dates[0].date() if dates else timezone.now().date()
        end_date = dates[-1].date() if dates else timezone.now().date()
        returns_dict = {d.date(): r for d, r in zip(dates, returns)}
        last_return = INITIAL_CAPITAL
        while current_date <= end_date:
            date_range.append(str(current_date))
            if current_date in returns_dict:
                last_return = returns_dict[current_date]
            returns_filled.append(last_return)
            current_date += timezone.timedelta(days=1)

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
                table=self.table_class(object_list),
                title="What if analysis",
                reward_per_trade=(
                    round(
                        (
                            ((total_returns / INITIAL_CAPITAL) ** (1 / (wins + losses)))
                            - 1
                        )
                        * 100,
                        2,
                    )
                    if total_returns
                    else 1
                ),
            )
        )
