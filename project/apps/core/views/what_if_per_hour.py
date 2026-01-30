from typing import List

from django.db.models import QuerySet, Q
from django.utils import timezone
from django.views.generic.edit import FormView

from project.apps.core.filters import PositionFilterSet
from project.apps.core.forms import WhatIfPerHourForm
from project.apps.core.models import Position, OHLCV
from project.apps.core.tables import WhatIfPerHourPositionTable


class PositionWhatIfPerHourBaseView(FormView):
    """List view for positions with table and filter functionality."""

    template_name = "core/what_if_per_hour.html"
    model = Position
    table_class = WhatIfPerHourPositionTable
    filterset_class = PositionFilterSet
    form_class = WhatIfPerHourForm

    def prepped_form_valid(self, form, filter_dict: dict, hour_field: str):
        if form.cleaned_data["start_date_lt"]:
            until_date = form.cleaned_data["start_date_lt"]
        else:
            until_date = timezone.now().date()
        table_rows: List[dict] = []
        for hour in range(24):
            table_row = {"hour": hour}
            positions: QuerySet[Position] = (
                self.model.objects.exclude(candles_before_entry__in=[1])
                .filter(
                    liquidation_amount__gte=2000,
                    timeframe="5m",
                    **filter_dict,
                    **{hour_field: hour},
                )
                .filter(
                    Q(
                        strategy_type="live",
                        confirmation_candles=1,
                    )
                    | Q(
                        strategy_type="reversed",
                        confirmation_candles__in=[1, 2],
                    )
                )
                .distinct()
            )
            if start_date_gte := form.cleaned_data["start_date_gte"]:
                positions = positions.filter(liquidation_datetime__gte=start_date_gte)
            if start_date_lt := form.cleaned_data["start_date_lt"]:
                positions = positions.filter(liquidation_datetime__lt=start_date_lt)
            if weekdays := form.cleaned_data["week_days"]:
                positions = positions.filter(
                    liquidation_datetime__week_day__in=weekdays
                )
            positions = positions.order_by("liquidation_datetime")

            total_wins = 0
            total_losses = 0
            six_month_wins = 0
            six_month_losses = 0
            three_month_wins = 0
            three_month_losses = 0
            tp: float = form.cleaned_data[f"tp"]
            sl: float = form.cleaned_data[f"sl"]
            for position in positions:
                position.what_if_returns = 0
                ohlcv_s = OHLCV.objects.filter(
                    datetime__gte=position.start,
                    datetime__lt=position.start + timezone.timedelta(days=28),
                    timeframe="5m",
                ).order_by("datetime")
                if ohlcv_s.exists():
                    entry_price = round(
                        (
                            ohlcv_s.first().open * 1.0001
                            if position.side == "SHORT"
                            else ohlcv_s.first().open * 0.9999
                        ),
                        1,
                    )
                for candle in ohlcv_s:
                    if position.side == "LONG":

                        # SL
                        if candle.low <= entry_price - (entry_price * sl / 100):
                            total_losses += 1
                            six_month_losses += (
                                1
                                if position.liquidation_datetime.date()
                                >= until_date - timezone.timedelta(days=180)
                                else 0
                            )
                            three_month_losses += (
                                1
                                if position.liquidation_datetime.date()
                                >= until_date - timezone.timedelta(days=90)
                                else 0
                            )
                            break

                        # TP
                        if candle.close >= entry_price + (entry_price * tp / 100):
                            total_wins += 1
                            six_month_wins += (
                                1
                                if position.liquidation_datetime.date()
                                >= until_date - timezone.timedelta(days=180)
                                else 0
                            )
                            three_month_wins += (
                                1
                                if position.liquidation_datetime.date()
                                >= until_date - timezone.timedelta(days=90)
                                else 0
                            )
                            break

                    if position.side == "SHORT":

                        # SL
                        if candle.high >= entry_price + (entry_price * sl / 100):
                            total_losses += 1
                            six_month_losses += (
                                1
                                if position.liquidation_datetime.date()
                                >= until_date - timezone.timedelta(days=180)
                                else 0
                            )
                            three_month_losses += (
                                1
                                if position.liquidation_datetime.date()
                                >= until_date - timezone.timedelta(days=90)
                                else 0
                            )
                            break

                        # TP
                        if candle.close <= entry_price - (entry_price * tp / 100):
                            total_wins += 1
                            six_month_wins += (
                                1
                                if position.liquidation_datetime.date()
                                >= until_date - timezone.timedelta(days=180)
                                else 0
                            )
                            three_month_wins += (
                                1
                                if position.liquidation_datetime.date()
                                >= until_date - timezone.timedelta(days=90)
                                else 0
                            )
                            break

            # nr of trades
            table_row["total_nr_of_trades"] = total_wins + total_losses
            table_row["six_month_nr_of_trades"] = six_month_wins + six_month_losses
            table_row["three_month_nr_of_trades"] = (
                three_month_wins + three_month_losses
            )

            # ratio
            total_ratio = round(
                ((total_wins / (total_wins + total_losses) * 100) if total_wins else 0),
                1,
            )
            table_row["total_ratio"] = total_ratio
            six_month_ratio = round(
                (
                    (six_month_wins / (six_month_wins + six_month_losses) * 100)
                    if six_month_wins
                    else 0
                ),
                1,
            )
            table_row["six_month_ratio"] = six_month_ratio
            three_month_ratio = round(
                (
                    (three_month_wins / (three_month_wins + three_month_losses) * 100)
                    if three_month_wins
                    else 0
                ),
                1,
            )
            table_row["three_month_ratio"] = three_month_ratio
            table_row["average_ratio"] = round(
                (total_ratio + six_month_ratio + three_month_ratio) / 3, 1
            )

            # nr of R's
            total_nr_of_r_s = round(
                (tp / sl * total_wins)  # win R's
                - (total_wins * 0.05)  # lost R's due to fees on wins
                - (total_losses)  # lost R's
                - (total_losses * 0.1),
                2,
            )
            table_row["total_nr_of_r_s"] = total_nr_of_r_s
            six_month_nr_of_r_s = round(
                (tp / sl * six_month_wins)
                - (six_month_wins * 0.05)
                - (six_month_losses)
                - (six_month_losses * 0.1),
                2,
            )
            table_row["six_month_nr_of_r_s"] = six_month_nr_of_r_s
            three_month_nr_of_r_s = round(
                (tp / sl * three_month_wins)
                - (three_month_wins * 0.05)
                - (three_month_losses)
                - (three_month_losses * 0.1),
                2,
            )
            table_row["three_month_nr_of_r_s"] = three_month_nr_of_r_s
            table_row["average_nr_of_r_s"] = round(
                (
                    total_nr_of_r_s
                    + (six_month_nr_of_r_s * 2)
                    + (three_month_nr_of_r_s * 4)
                )
                / 3,
                2,
            )
            print(table_row)
            table_rows.append(table_row)

        return self.render_to_response(
            self.get_context_data(
                form=form,
                table=self.table_class(table_rows),
                title="What if per hour analysis",
            )
        )


class PositionWhatIfPerHourByLiquidationView(PositionWhatIfPerHourBaseView):
    def form_valid(self, form):
        return self.prepped_form_valid(
            form=form,
            filter_dict={"start__hour__in": form.cleaned_data["hours"]},
            hour_field="liquidation_datetime__hour",
        )


class PositionWhatIfPerHourByEntryView(PositionWhatIfPerHourBaseView):
    def form_valid(self, form):
        return self.prepped_form_valid(
            form=form,
            filter_dict={"liquidation_datetime__hour__in": form.cleaned_data["hours"]},
            hour_field="start__hour",
        )
