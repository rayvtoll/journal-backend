import os
from typing import Tuple
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import random
import pandas as pd
import seaborn as sns

from django.db.models import QuerySet, Q
from django.utils import timezone
from django.views.generic.edit import FormView

from project.apps.core.filters import PositionFilterSet
from project.apps.core.forms import WhatIfAlgorithmForm
from project.apps.core.models import Position, OHLCV
from project.apps.core.tables import WhatIfPositionTable

from .helpers import (
    COLOR_LIST,
    INITIAL_CAPITAL,
    SNS_THEME,
    image_encoder,
    plotter,
    WinStreak,
)

BLOFIN_MARKET_ORDER_FEE = 0.06 / 100  # 0.06% for non VIP users
BLOFIN_LIMIT_ORDER_FEE = 0.02 / 100  # 0.002% for non VIP users


def process_position_what_if(
    wins: int,
    losses: int,
    win_streak: WinStreak,
    total_returns: float,
    position: Position,
    object_list: list[Position],
    returns: list[float],
    dates: list[timezone.datetime],
) -> Tuple[int, int, float]:
    win = position.what_if_returns > 0
    if win:
        wins += 1
        win_streak.record_win()
    else:
        losses += 1
        win_streak.record_loss()
    total_returns += position.what_if_returns
    position.what_if_returns = f"$ {round(position.what_if_returns, 2):,}"
    object_list.insert(0, position)
    returns.append(total_returns)
    dates.append(position.start)
    return wins, losses, total_returns


def process_tp(
    use_tp: bool,
    tp_finished: bool,
    direction: str,
    general_tp: float,
    tp: float,
    tp_amount: float,
    position: Position,
    candle,
    amount: float,
) -> Tuple[bool, float]:
    if use_tp and not tp_finished:
        if direction == "long" and candle.high >= position.entry_price + (
            position.entry_price * (tp / 100 * general_tp / 100)
        ):
            fees_for_closing = (
                (position.amount * tp_amount / 100)
                * position.entry_price
                * BLOFIN_LIMIT_ORDER_FEE
            )
            position.what_if_returns -= fees_for_closing
            local_returns = (position.entry_price * (general_tp * tp / 100) / 100) * (
                amount * tp_amount / 100
            )
            position.what_if_returns += local_returns
            amount = amount - (amount * tp_amount / 100)
            return True, amount
        if direction == "short" and candle.low <= position.entry_price - (
            position.entry_price * (tp / 100 * general_tp / 100)
        ):
            fees_for_closing = (
                (position.amount * tp_amount / 100)
                * position.entry_price
                * BLOFIN_LIMIT_ORDER_FEE
            )
            position.what_if_returns -= fees_for_closing
            local_returns = (position.entry_price * (general_tp * tp / 100) / 100) * (
                position.amount * tp_amount / 100
            )
            position.what_if_returns += local_returns
            amount = amount - (position.amount * tp_amount / 100)
            return True, amount
    return tp_finished, amount


class PositionWhatIfAlgorithmView(FormView):
    """List view for positions with table and filter functionality."""

    template_name = "core/what_if.html"
    model = Position
    table_class = WhatIfPositionTable
    filterset_class = PositionFilterSet
    form_class = WhatIfAlgorithmForm

    def form_valid(self, form: WhatIfAlgorithmForm):
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

        positions: QuerySet[Position] = self.model.objects.exclude(
            candles_before_entry__in=form.cleaned_data["candles_before_entry_not"]
        )
        positions = positions.filter(
            Q(
                strategy_type="live",
                confirmation_candles__in=form.cleaned_data["live_confirmation_candles"],
            )
            | Q(
                strategy_type="reversed",
                confirmation_candles__in=form.cleaned_data[
                    "reversed_confirmation_candles"
                ],
            )
        ).distinct()
        positions = positions.filter(
            timeframe="5m",
            liquidation_datetime__week_day__in=[2, 3, 4, 5, 6],  # monday-friday
            liquidation_datetime__hour__in=[
                2,
                3,
                4,
                14,
                15,
                16,
            ],  # 2-4am and 2-4pm
        )
        if strategy_types := form.cleaned_data["strategy_types"]:
            positions = positions.filter(strategy_type__in=strategy_types)
        if start_date_gte := form.cleaned_data["start_date_gte"]:
            positions = positions.filter(liquidation_datetime__gte=start_date_gte)
        if start_date_lt := form.cleaned_data["start_date_lt"]:
            positions = positions.filter(liquidation_datetime__lt=start_date_lt)
        if min_liq := form.cleaned_data.get("min_liquidation_amount"):
            positions = positions.filter(liquidation_amount__gte=min_liq)
        if max_liq := form.cleaned_data.get("max_liquidation_amount"):
            positions = positions.filter(liquidation_amount__lte=max_liq)

        positions = positions.distinct().order_by("liquidation_datetime")

        returns = []
        dates = []
        total_returns = INITIAL_CAPITAL
        wins = 0
        losses = 0
        win_streak = WinStreak()
        sl: float = 1.0
        sl_to_entry: float = form.cleaned_data["sl_to_entry"]
        use_tp1: bool = form.cleaned_data["use_tp1"]
        tp1: float = form.cleaned_data["tp1"]
        tp1_amount: float = form.cleaned_data["tp1_amount"]
        use_tp2: bool = form.cleaned_data["use_tp2"]
        tp2: float = form.cleaned_data["tp2"]
        tp2_amount: float = form.cleaned_data["tp2_amount"]
        use_tp3: bool = form.cleaned_data["use_tp3"]
        tp3: float = form.cleaned_data["tp3"]
        tp3_amount: float = form.cleaned_data["tp3_amount"]
        use_tp4: bool = form.cleaned_data["use_tp4"]
        tp4: float = form.cleaned_data["tp4"]
        tp4_amount: float = form.cleaned_data["tp4_amount"]
        no_overlap: bool = form.cleaned_data["no_overlap"]
        use_trailing_sl: bool = form.cleaned_data["use_trailing_sl"]
        trailing_sl: float = form.cleaned_data["trailing_sl"]
        compound: bool = form.cleaned_data["compound"]
        last_long_candle_datetime = None
        last_short_candle_datetime = None
        percentage_per_trade: float = form.cleaned_data["percentage_per_trade"]
        use_rsi: bool = form.cleaned_data["use_rsi"]
        rsi_lower: int = form.cleaned_data["rsi_lower"]
        rsi_upper: int = form.cleaned_data["rsi_upper"]
        rsi_sell_percentage: float = form.cleaned_data["rsi_sell_percentage"]

        object_list: list[Position] = []
        for position in positions:
            try:
                try:
                    algorithm_input: pd.DataFrame = pd.read_csv(
                        f"data/algorithm_input-{position.liquidation_datetime.date()}-{position.strategy_type}.csv"
                    )
                except:
                    algorithm_input: pd.DataFrame = pd.read_csv(
                        f"data/algorithm_input-{position.liquidation_datetime.date().replace(day=2)}-{position.strategy_type}.csv"
                    )
            except:
                file_names = os.listdir("data/")
                file_names = [
                    name
                    for name in os.listdir("data/")
                    if os.path.isfile(os.path.join("data/", name))
                ]
                file_names = [
                    name
                    for name in file_names
                    if (
                        name.startswith("algorithm_input-")
                        and position.strategy_type in name
                    )
                ]
                file_names.sort()
                last_file_name = file_names[-1]
                algorithm_input: pd.DataFrame = pd.read_csv(f"data/{last_file_name}")
            hour = position.liquidation_datetime.hour
            trade: bool = False
            tp: float = 0.0
            weight: float = 0.0
            for row in algorithm_input.itertuples():
                if row.hour_of_the_day == hour:
                    trade, tp, weight = (
                        row.trade,
                        row.tp_percentage,
                        row.position_size_weighted,
                    )

            if not trade:
                continue

            position.what_if_returns = 0
            use_sl_to_entry: bool = form.cleaned_data["use_sl_to_entry"]
            iso_datetime = (
                f"{position.start.year}-"
                f"{position.start.month:02d}-"
                f"{position.start.day:02d} "
                f"{position.start.hour:02d}:{position.start.minute:02d}:00"
            )
            ohlcv_s = OHLCV.objects.filter(
                datetime__gte=timezone.datetime.fromisoformat(iso_datetime),
                datetime__lt=position.start + timezone.timedelta(days=28),
                timeframe="5m",
            ).order_by("datetime")
            tp1_finished = False
            tp2_finished = False
            tp3_finished = False
            tp4_finished = False
            if ohlcv_s.exists():
                position.entry_price = round(
                    (
                        ohlcv_s.first().open * 1.0001
                        if position.side == "SHORT"
                        else ohlcv_s.first().open * 0.9999
                    ),
                    1,
                )
                position.amount = round(
                    (total_returns if compound else INITIAL_CAPITAL)
                    / sl
                    / position.entry_price
                    * percentage_per_trade
                    * weight,
                    4,
                )
                amount = position.amount
                fees_for_opening = (
                    position.amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                )
                position.what_if_returns -= fees_for_opening
                if use_trailing_sl:
                    position_sl_price = (
                        position.entry_price * (1 - trailing_sl / 100)
                        if position.side == "LONG"
                        else position.entry_price * (1 + trailing_sl / 100)
                    )

            # prevent overlapping trades if no_overlap is checked
            if no_overlap:
                if (
                    position.side == "LONG"
                    and last_long_candle_datetime
                    and ohlcv_s.first().datetime < last_long_candle_datetime
                ) or (
                    position.side == "SHORT"
                    and last_short_candle_datetime
                    and ohlcv_s.first().datetime < last_short_candle_datetime
                ):
                    continue

            rsi_candles = []
            for candle in ohlcv_s:

                if position.side == "LONG":

                    # trailing SL
                    if use_trailing_sl:
                        position_sl_price = max(
                            position_sl_price,
                            position.entry_price - (position.entry_price * sl / 100),
                            candle.high - (candle.high * trailing_sl / 100),
                        )

                        if candle.low <= position_sl_price:
                            position.closing_price = round(position_sl_price, 1)
                            fees_for_closing = (
                                amount
                                * position.closing_price
                                * BLOFIN_MARKET_ORDER_FEE
                            )
                            position.what_if_returns -= fees_for_closing
                            loss_or_win = (
                                position.entry_price - position_sl_price
                            ) * amount
                            position.what_if_returns -= loss_or_win
                            win = position.what_if_returns > 0
                            if win:
                                wins += 1
                                win_streak.record_win()
                            else:
                                losses += 1
                                win_streak.record_loss()
                            total_returns += position.what_if_returns
                            position.what_if_returns = (
                                f"$ {round(position.what_if_returns, 2):,}"
                            )
                            object_list.insert(0, position)
                            returns.append(total_returns)
                            dates.append(position.start)
                            last_long_candle_datetime = candle.datetime
                            break

                    # SL
                    if candle.low <= position.entry_price - (
                        position.entry_price * sl / 100
                    ):
                        position.closing_price = round(
                            position.entry_price - (position.entry_price * sl / 100), 1
                        )
                        fees_for_closing = (
                            amount * position.closing_price * BLOFIN_MARKET_ORDER_FEE
                        )
                        position.what_if_returns -= fees_for_closing
                        loss = (position.entry_price * sl / 100) * amount
                        position.what_if_returns -= loss
                        wins, losses, total_returns = process_position_what_if(
                            wins,
                            losses,
                            win_streak,
                            total_returns,
                            position,
                            object_list,
                            returns,
                            dates,
                        )
                        last_long_candle_datetime = candle.datetime
                        break

                    # SL to entry
                    if use_sl_to_entry and candle.high > position.entry_price + (
                        position.entry_price * (sl_to_entry / 100 * tp / 100)
                    ):
                        sl = -sl
                        use_sl_to_entry = False  # only use once

                    # TP1
                    tp1_finished, amount = process_tp(
                        use_tp=use_tp1,
                        tp_finished=tp1_finished,
                        direction="long",
                        general_tp=tp,
                        tp=tp1,
                        tp_amount=tp1_amount,
                        position=position,
                        candle=candle,
                        amount=amount,
                    )

                    # TP2
                    tp2_finished, amount = process_tp(
                        use_tp=use_tp2,
                        tp_finished=tp2_finished,
                        direction="long",
                        general_tp=tp,
                        tp=tp2,
                        tp_amount=tp2_amount,
                        position=position,
                        candle=candle,
                        amount=amount,
                    )

                    # TP3
                    tp3_finished, amount = process_tp(
                        use_tp=use_tp3,
                        tp_finished=tp3_finished,
                        direction="long",
                        general_tp=tp,
                        tp=tp3,
                        tp_amount=tp3_amount,
                        position=position,
                        candle=candle,
                        amount=amount,
                    )

                    # TP4
                    tp4_finished, amount = process_tp(
                        use_tp=use_tp4,
                        tp_finished=tp4_finished,
                        direction="long",
                        general_tp=tp,
                        tp=tp4,
                        tp_amount=tp4_amount,
                        position=position,
                        candle=candle,
                        amount=amount,
                    )

                    # final TP
                    if candle.high >= position.entry_price + (
                        position.entry_price * tp / 100
                    ):
                        position.closing_price = round(
                            position.entry_price + (position.entry_price * tp / 100), 1
                        )
                        fees_for_closing = (
                            amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                        )
                        position.what_if_returns -= fees_for_closing
                        local_win = (position.entry_price * tp / 100) * amount
                        position.what_if_returns += local_win
                        wins, losses, total_returns = process_position_what_if(
                            wins,
                            losses,
                            win_streak,
                            total_returns,
                            position,
                            object_list,
                            returns,
                            dates,
                        )
                        last_long_candle_datetime = candle.datetime
                        break

                if position.side == "SHORT":

                    # trailing SL
                    if use_trailing_sl:
                        position_sl_price = min(
                            position_sl_price,
                            position.entry_price + (position.entry_price * sl / 100),
                            candle.low + (candle.low * trailing_sl / 100),
                        )

                        if candle.high >= position_sl_price:
                            position.closing_price = round(position_sl_price, 1)
                            fees_for_closing = (
                                amount
                                * position.closing_price
                                * BLOFIN_MARKET_ORDER_FEE
                            )
                            position.what_if_returns -= fees_for_closing
                            loss_or_win = (
                                position_sl_price - position.entry_price
                            ) * amount
                            position.what_if_returns -= loss_or_win
                            wins, losses, total_returns = process_position_what_if(
                                wins,
                                losses,
                                win_streak,
                                total_returns,
                                position,
                                object_list,
                                returns,
                                dates,
                            )
                            last_short_candle_datetime = candle.datetime
                            break

                    # SL
                    if candle.high >= position.entry_price + (
                        position.entry_price * sl / 100
                    ):
                        position.closing_price = round(
                            position.entry_price + (position.entry_price * sl / 100), 1
                        )
                        fees_for_closing = (
                            amount * position.closing_price * BLOFIN_MARKET_ORDER_FEE
                        )
                        position.what_if_returns -= fees_for_closing
                        loss = (position.entry_price * sl / 100) * amount
                        position.what_if_returns -= loss
                        wins, losses, total_returns = process_position_what_if(
                            wins,
                            losses,
                            win_streak,
                            total_returns,
                            position,
                            object_list,
                            returns,
                            dates,
                        )
                        last_short_candle_datetime = candle.datetime
                        break

                    # SL to entry
                    if use_sl_to_entry and candle.low < position.entry_price - (
                        position.entry_price * (sl_to_entry / 100 * tp / 100)
                    ):
                        sl = -sl
                        use_sl_to_entry = False  # only use once

                    # TP1
                    tp1_finished, amount = process_tp(
                        use_tp=use_tp1,
                        tp_finished=tp1_finished,
                        direction="long",
                        general_tp=tp,
                        tp=tp1,
                        tp_amount=tp1_amount,
                        position=position,
                        candle=candle,
                        amount=amount,
                    )

                    # TP2
                    tp2_finished, amount = process_tp(
                        use_tp=use_tp2,
                        tp_finished=tp2_finished,
                        direction="short",
                        general_tp=tp,
                        tp=tp2,
                        tp_amount=tp2_amount,
                        position=position,
                        candle=candle,
                        amount=amount,
                    )

                    # TP3
                    tp3_finished, amount = process_tp(
                        use_tp=use_tp3,
                        tp_finished=tp3_finished,
                        direction="short",
                        general_tp=tp,
                        tp=tp3,
                        tp_amount=tp3_amount,
                        position=position,
                        candle=candle,
                        amount=amount,
                    )

                    # TP4
                    tp4_finished, amount = process_tp(
                        use_tp=use_tp4,
                        tp_finished=tp4_finished,
                        direction="short",
                        general_tp=tp,
                        tp=tp4,
                        tp_amount=tp4_amount,
                        position=position,
                        candle=candle,
                        amount=amount,
                    )

                    # final TP
                    if candle.low <= position.entry_price - (
                        position.entry_price * tp / 100
                    ):
                        position.closing_price = round(
                            position.entry_price - (position.entry_price * tp / 100), 1
                        )
                        fees_for_closing = (
                            amount * position.closing_price * BLOFIN_LIMIT_ORDER_FEE
                        )
                        position.what_if_returns -= fees_for_closing
                        local_wins = (position.entry_price * tp / 100) * amount
                        position.what_if_returns += local_wins
                        wins, losses, total_returns = process_position_what_if(
                            wins,
                            losses,
                            win_streak,
                            total_returns,
                            position,
                            object_list,
                            returns,
                            dates,
                        )
                        last_short_candle_datetime = candle.datetime
                        break

                rsi_candles.append(candle)
                if (
                    use_rsi
                    and len(rsi_candles) >= 14
                    and (
                        candle.low
                        <= position.entry_price
                        - (position.entry_price * (50 / 100 * tp / 100))
                        or candle.high
                        >= position.entry_price
                        + (position.entry_price * (50 / 100 * tp / 100))
                    )
                ):
                    rsi_candles = rsi_candles[-14:]  # keep only last 14 candles
                    # calculate RSI
                    rsi_gains = []
                    rsi_losses = []
                    for i in range(0, 14):
                        change = rsi_candles[i].close - rsi_candles[i].open
                        if change > 0:
                            rsi_gains.append(change)
                        else:
                            rsi_losses.append(abs(change))
                    average_gain = sum(rsi_gains) / 14 if rsi_gains else 0
                    average_loss = sum(rsi_losses) / 14 if rsi_losses else 0
                    if average_loss == 0:
                        rsi = 100
                    else:
                        rs = average_gain / average_loss
                        rsi = 100 - (100 / (1 + rs))

                    # check RSI conditions
                    if position.side == "LONG" and rsi >= rsi_upper and amount > 0:
                        sell_amount = amount * (rsi_sell_percentage / 100)
                        fees_for_closing = (
                            sell_amount * candle.close * BLOFIN_MARKET_ORDER_FEE
                        )
                        position.what_if_returns -= fees_for_closing
                        local_win = (candle.close - position.entry_price) * sell_amount
                        position.what_if_returns += local_win
                        amount -= sell_amount

                    if position.side == "SHORT" and rsi <= rsi_lower and amount > 0:
                        sell_amount = amount * (rsi_sell_percentage / 100)
                        fees_for_closing = (
                            sell_amount * candle.close * BLOFIN_MARKET_ORDER_FEE
                        )
                        position.what_if_returns -= fees_for_closing
                        local_win = (position.entry_price - candle.close) * sell_amount
                        position.what_if_returns += local_win
                        amount -= sell_amount

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
        c = random.choice(COLOR_LIST)
        use_log = form.cleaned_data.get("use_log_scale", False)
        if use_log:
            ax_func = getattr(ax, "semilogy")
        else:
            ax_func = getattr(ax, "plot")
        ax_func(
            x_as_data,
            y_as_data,
            color=c,
            label="Capital",
            linewidth=2,
            markersize=8,
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
                ratio=(wins / (wins + losses) * 100) if wins else 0,
                wins=wins,
                losses=losses,
                nr_of_trades=wins + losses,
                table=self.table_class(object_list),
                title="What if analysis",
                reward_per_trade=(
                    round(
                        (
                            (
                                (
                                    (total_returns / INITIAL_CAPITAL)
                                    ** (1 / (wins + losses))
                                )
                                - 1
                            )
                            if (wins or losses)
                            else 0
                        )
                        * 100,
                        2,
                    )
                    if total_returns
                    else 1
                ),
                longest_win_streak=win_streak.longest_win_streak,
                longest_loss_streak=win_streak.longest_loss_streak,
            )
        )
