import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import random
import seaborn as sns

from django.db.models import QuerySet, Q
from django.utils import timezone
from django.views.generic.edit import FormView

from project.apps.core.filters import PositionFilterSet
from project.apps.core.forms import WhatIfForm
from project.apps.core.models import Position, OHLCV
from project.apps.core.tables import WhatIfPositionTable

from .helpers import COLOR_LIST, INITIAL_CAPITAL, SNS_THEME, image_encoder, plotter

BLOFIN_MARKET_ORDER_FEE = 0.06 / 100  # 0.06% for non VIP users
BLOFIN_LIMIT_ORDER_FEE = 0.02 / 100  # 0.002% for non VIP users


class PositionWhatIfView(FormView):
    """List view for positions with table and filter functionality."""

    template_name = "core/what_if.html"
    model = Position
    table_class = WhatIfPositionTable
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

        positions: QuerySet[Position] = self.model.objects.filter(
            Q(
                strategy_type="live",
                candles_before_entry__in=form.cleaned_data["live_candles_before_entry"],
            )
            | Q(
                strategy_type="reversed",
                candles_before_entry__in=form.cleaned_data[
                    "reversed_candles_before_entry"
                ],
            )
        ).distinct()
        positions = positions.filter(timeframe="5m")
        if strategy_types := form.cleaned_data["strategy_types"]:
            positions = positions.filter(strategy_type__in=strategy_types)
        if start_date_gte := form.cleaned_data["start_date_gte"]:
            positions = positions.filter(start__gte=start_date_gte)
        if start_date_lt := form.cleaned_data["start_date_lt"]:
            positions = positions.filter(start__lt=start_date_lt)
        if weekdays := form.cleaned_data["week_days"]:
            positions = positions.filter(liquidation_datetime__week_day__in=weekdays)
        if hours := form.cleaned_data["hours"]:
            positions = positions.filter(liquidation_datetime__hour__in=hours)
        if min_liq := form.cleaned_data.get("min_liquidation_amount"):
            positions = positions.filter(liquidation_amount__gte=min_liq)
        if max_liq := form.cleaned_data.get("max_liquidation_amount"):
            positions = positions.filter(liquidation_amount__lte=max_liq)

        positions = positions.order_by("start")

        returns = []
        dates = []
        total_returns = INITIAL_CAPITAL
        wins = 0
        losses = 0
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
        use_tp5: bool = form.cleaned_data["use_tp5"]
        tp5: float = form.cleaned_data["tp5"]
        tp5_amount: float = form.cleaned_data["tp5_amount"]
        use_tp6: bool = form.cleaned_data["use_tp6"]
        tp6: float = form.cleaned_data["tp6"]
        tp6_amount: float = form.cleaned_data["tp6_amount"]
        use_tp7: bool = form.cleaned_data["use_tp7"]
        tp7: float = form.cleaned_data["tp7"]
        tp7_amount: float = form.cleaned_data["tp7_amount"]
        use_tp8: bool = form.cleaned_data["use_tp8"]
        tp8: float = form.cleaned_data["tp8"]
        tp8_amount: float = form.cleaned_data["tp8_amount"]
        use_tp9: bool = form.cleaned_data["use_tp9"]
        tp9: float = form.cleaned_data["tp9"]
        tp9_amount: float = form.cleaned_data["tp9_amount"]
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
            match position.strategy_type:
                case "reversed":
                    sl: float = form.cleaned_data["reversed_sl"]
                    tp: float = form.cleaned_data["reversed_tp"]
                case "live" | _:
                    sl: float = form.cleaned_data["live_sl"]
                    tp: float = form.cleaned_data["live_tp"]
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
            tp5_finished = False
            tp6_finished = False
            tp7_finished = False
            tp8_finished = False
            tp9_finished = False
            if ohlcv_s.exists():
                position.entry_price = round(
                    (
                        ohlcv_s.first().open * 1.0001
                        if position.side == "SHORT"
                        else ohlcv_s.first().open * 0.9999
                    ),
                    1,
                )
                position.amount = (
                    (total_returns if compound else INITIAL_CAPITAL)
                    / sl
                    / position.entry_price
                    * percentage_per_trade
                )
                amount = position.amount
                fees_for_opening = (
                    position.amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                )
                total_returns -= fees_for_opening
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
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            loss_or_win = (
                                position.entry_price - position_sl_price
                            ) * amount
                            total_returns -= loss_or_win
                            position.what_if_returns -= loss_or_win
                            position.what_if_returns = (
                                f"$ {round(position.what_if_returns, 2):,}"
                            )
                            object_list.insert(0, position)
                            returns.append(total_returns)
                            dates.append(position.start)
                            losses += 1
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
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
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
                        last_long_candle_datetime = candle.datetime
                        break

                    # SL to entry
                    if use_sl_to_entry and candle.high > position.entry_price + (
                        position.entry_price * (sl_to_entry / 100 * tp / 100)
                    ):
                        sl = -sl
                        use_sl_to_entry = False  # only use once

                    # TP1
                    if use_tp1 and not tp1_finished:
                        if candle.high >= position.entry_price + (
                            position.entry_price * (tp1 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp1_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp1 / 100) / 100
                            ) * (amount * tp1_amount / 100)
                            total_returns += local_returns
                            position.what_if_returns += local_returns
                            amount = amount - (amount * tp1_amount / 100)
                            tp1_finished = True

                    # TP2
                    if use_tp2 and not tp2_finished:
                        if candle.high >= position.entry_price + (
                            position.entry_price * (tp2 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp2 / 100) / 100
                            ) * (amount * tp2_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (amount * tp2_amount / 100)
                            tp2_finished = True

                    # TP3
                    if use_tp3 and not tp3_finished:
                        if candle.high >= position.entry_price + (
                            position.entry_price * (tp3 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp3 / 100) / 100
                            ) * (amount * tp3_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (amount * tp3_amount / 100)
                            tp3_finished = True

                    # TP4
                    if use_tp4 and not tp4_finished:
                        if candle.high >= position.entry_price + (
                            position.entry_price * (tp4 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp4 / 100) / 100
                            ) * (amount * tp4_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (amount * tp4_amount / 100)
                            tp4_finished = True

                    # TP5
                    if use_tp5 and not tp5_finished:
                        if candle.high >= position.entry_price + (
                            position.entry_price * (tp5 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp5 / 100) / 100
                            ) * (amount * tp5_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (amount * tp5_amount / 100)
                            tp5_finished = True

                    # TP6
                    if use_tp6 and not tp6_finished:
                        if candle.high >= position.entry_price + (
                            position.entry_price * (tp6 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp6 / 100) / 100
                            ) * (amount * tp6_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (amount * tp6_amount / 100)
                            tp6_finished = True

                    # TP7
                    if use_tp7 and not tp7_finished:
                        if candle.high >= position.entry_price + (
                            position.entry_price * (tp7 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp7 / 100) / 100
                            ) * (amount * tp7_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (amount * tp7_amount / 100)
                            tp7_finished = True

                    # TP8
                    if use_tp8 and not tp8_finished:
                        if candle.high >= position.entry_price + (
                            position.entry_price * (tp8 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp8 / 100) / 100
                            ) * (amount * tp8_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (amount * tp8_amount / 100)
                            tp8_finished = True

                    # TP9
                    if use_tp9 and not tp9_finished:
                        if candle.high >= position.entry_price + (
                            position.entry_price * (tp9 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp9 / 100) / 100
                            ) * (amount * tp9_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (amount * tp9_amount / 100)
                            tp9_finished = True

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
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
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
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            loss_or_win = (
                                position_sl_price - position.entry_price
                            ) * amount
                            total_returns -= loss_or_win
                            position.what_if_returns -= loss_or_win
                            position.what_if_returns = (
                                f"$ {round(position.what_if_returns, 2):,}"
                            )
                            object_list.insert(0, position)
                            returns.append(total_returns)
                            dates.append(position.start)
                            losses += 1
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
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
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
                        last_short_candle_datetime = candle.datetime
                        break

                    # SL to entry
                    if use_sl_to_entry and candle.low < position.entry_price - (
                        position.entry_price * (sl_to_entry / 100 * tp / 100)
                    ):
                        sl = -sl
                        use_sl_to_entry = False  # only use once

                    # TP1
                    if use_tp1 and not tp1_finished:
                        if candle.low <= position.entry_price - (
                            position.entry_price * (tp1 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp1_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp1 / 100) / 100
                            ) * (position.amount * tp1_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (position.amount * tp1_amount / 100)
                            tp1_finished = True

                    # TP2
                    if use_tp2 and not tp2_finished:
                        if candle.low <= position.entry_price - (
                            position.entry_price * (tp2 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp2_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp2 / 100) / 100
                            ) * (position.amount * tp2_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (position.amount * tp2_amount / 100)
                            tp2_finished = True

                    # TP3
                    if use_tp3 and not tp3_finished:
                        if candle.low <= position.entry_price - (
                            position.entry_price * (tp3 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp3_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp3 / 100) / 100
                            ) * (position.amount * tp3_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (position.amount * tp3_amount / 100)
                            tp3_finished = True

                    # TP4
                    if use_tp4 and not tp4_finished:
                        if candle.low <= position.entry_price - (
                            position.entry_price * (tp4 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp4_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp4 / 100) / 100
                            ) * (position.amount * tp4_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (position.amount * tp4_amount / 100)
                            tp4_finished = True

                    # TP5
                    if use_tp5 and not tp5_finished:
                        if candle.low <= position.entry_price - (
                            position.entry_price * (tp5 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp5_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp5 / 100) / 100
                            ) * (position.amount * tp5_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (position.amount * tp5_amount / 100)
                            tp5_finished = True

                    # TP6
                    if use_tp6 and not tp6_finished:
                        if candle.low <= position.entry_price - (
                            position.entry_price * (tp6 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp6_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp6 / 100) / 100
                            ) * (position.amount * tp6_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (position.amount * tp6_amount / 100)
                            tp6_finished = True

                    # TP7
                    if use_tp7 and not tp7_finished:
                        if candle.low <= position.entry_price - (
                            position.entry_price * (tp7 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp7_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp7 / 100) / 100
                            ) * (position.amount * tp7_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (position.amount * tp7_amount / 100)
                            tp7_finished = True

                    # TP8
                    if use_tp8 and not tp8_finished:
                        if candle.low <= position.entry_price - (
                            position.entry_price * (tp8 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp8_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp8 / 100) / 100
                            ) * (position.amount * tp8_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (position.amount * tp8_amount / 100)
                            tp8_finished = True

                    # TP9
                    if use_tp9 and not tp9_finished:
                        if candle.low <= position.entry_price - (
                            position.entry_price * (tp9 / 100 * tp / 100)
                        ):
                            fees_for_closing = (
                                (position.amount * tp9_amount / 100)
                                * position.entry_price
                                * BLOFIN_LIMIT_ORDER_FEE
                            )
                            total_returns -= fees_for_closing
                            position.what_if_returns -= fees_for_closing
                            local_returns = (
                                position.entry_price * (tp * tp9 / 100) / 100
                            ) * (position.amount * tp9_amount / 100)
                            position.what_if_returns += local_returns
                            total_returns += local_returns
                            amount = amount - (position.amount * tp9_amount / 100)
                            tp9_finished = True

                    # final TP
                    if candle.low <= position.entry_price - (
                        position.entry_price * tp / 100
                    ):
                        position.closing_price = round(
                            position.entry_price + (position.entry_price * tp / 100), 1
                        )
                        fees_for_closing = (
                            amount * position.closing_price * BLOFIN_LIMIT_ORDER_FEE
                        )
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
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
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
                        local_win = (candle.close - position.entry_price) * sell_amount
                        total_returns += local_win
                        position.what_if_returns += local_win
                        amount -= sell_amount

                    if position.side == "SHORT" and rsi <= rsi_lower and amount > 0:
                        sell_amount = amount * (rsi_sell_percentage / 100)
                        fees_for_closing = (
                            sell_amount * candle.close * BLOFIN_MARKET_ORDER_FEE
                        )
                        total_returns -= fees_for_closing
                        position.what_if_returns -= fees_for_closing
                        local_win = (position.entry_price - candle.close) * sell_amount
                        total_returns += local_win
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
                ratio=(wins / (wins + losses) * 100) if wins and losses else 0,
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
