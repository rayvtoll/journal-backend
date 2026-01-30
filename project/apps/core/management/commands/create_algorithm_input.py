import csv
from datetime import timedelta, date
import pandas as pd
from typing import List

from django.core.management.base import BaseCommand
from django.db.models import QuerySet, Q
from django.utils import timezone

from project.apps.core.models import Position, OHLCV


TP_RANGE = 1, 6  # TP 1% to 5%


class Command(BaseCommand):
    help = "Get input data for algorithm."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            help="year for which to create the algorithm input data",
        )
        parser.add_argument(
            "--month",
            type=int,
            help="month for which to create the algorithm input data",
        )
        parser.add_argument(
            "--day",
            type=int,
            help="day for which to create the algorithm input data",
            default=1,
        )

    def run_algorithm_input(
        self, until_date: date, tp: int, strategy_type: str, **filter_kwargs
    ) -> List[dict]:
        return_list: List[dict] = []
        for hour in range(24):
            return_row: dict = {"hour": hour}
            positions: QuerySet[Position] = (
                Position.objects.exclude(candles_before_entry=1)
                .filter(
                    liquidation_amount__gte=2000,
                    timeframe="5m",
                    liquidation_datetime__gte=until_date - timedelta(days=365),
                    liquidation_datetime__lt=until_date,
                    liquidation_datetime__hour=hour,
                    liquidation_datetime__week_day__in=[2, 3, 4, 5, 6],  # monday-friday
                    strategy_type=strategy_type,
                    **filter_kwargs,
                )
                .distinct()
                .order_by("liquidation_datetime")
            )

            total_wins = 0
            total_losses = 0
            six_month_wins = 0
            six_month_losses = 0
            three_month_wins = 0
            three_month_losses = 0
            sl: float = 1
            for position in positions:
                position.what_if_returns = 0
                last_candle = min(
                    position.start + timezone.timedelta(days=28),
                    timezone.datetime(
                        until_date.year, until_date.month, until_date.day
                    ),
                )
                ohlcv_s = OHLCV.objects.filter(
                    datetime__gte=position.start,
                    datetime__lt=last_candle,
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

            # nr of R's
            total_nr_of_r_s = round(
                (tp / sl * total_wins)  # win R's
                - (total_wins * 0.05)  # lost R's due to fees on wins
                - (total_losses)  # lost R's
                - (total_losses * 0.1),  # lost R's due to fees on losses
                2,
            )
            six_month_nr_of_r_s = round(
                (tp / sl * six_month_wins)
                - (six_month_wins * 0.05)
                - (six_month_losses)
                - (six_month_losses * 0.1),
                2,
            )
            three_month_nr_of_r_s = round(
                (tp / sl * three_month_wins)
                - (three_month_wins * 0.05)
                - (three_month_losses)
                - (three_month_losses * 0.1),
                2,
            )
            return_row[f"tp_{tp}"] = round(
                (
                    total_nr_of_r_s
                    + (six_month_nr_of_r_s * 2)
                    + (three_month_nr_of_r_s * 4)
                )
                / 3,
                2,
            )
            return_row["trades"] = total_losses + total_wins
            return_list.append(return_row)
        return return_list

    def handle(self, *args, **options):
        # get until_date
        if options["year"] and options["month"] and options["day"]:
            year = options["year"]
            month = options["month"]
            day = options["day"]
            till_date = date(year, month, day)
        else:
            till_date = timezone.now().date() - timedelta(days=1)

        for strategy_type in ["live", "reversed"]:
            day_dataframe = pd.DataFrame()
            if strategy_type == "live":
                filter_kwargs = {"confirmation_candles": 1}
            else:
                filter_kwargs = {"confirmation_candles__in": [1, 2]}
            for tp in range(*TP_RANGE):
                result = self.run_algorithm_input(
                    till_date, tp, strategy_type, **filter_kwargs
                )
                tp_dataframe = pd.DataFrame(result)
                if day_dataframe.empty:
                    day_dataframe = tp_dataframe[["hour", "trades", f"tp_{tp}"]]
                else:
                    day_dataframe = pd.merge(
                        day_dataframe,
                        tp_dataframe[["hour", f"tp_{tp}"]],
                        on="hour",
                    )
            # write to csv
            day_dataframe.to_csv(
                f"data/data-{till_date}-{strategy_type}.csv", index=False
            )

            # write csv header
            with open(
                f"data/algorithm_input-{till_date + timedelta(days=1)}-{strategy_type}.csv",
                "w",
                newline="",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "hour_of_the_day",
                        "trade",
                        "position_size_weighted",
                        "tp_percentage",
                    ]
                )

            df = pd.read_csv(f"data/data-{till_date}-{strategy_type}.csv")
            for row in df.itertuples(index=False):
                tp_percentage = max(
                    [getattr(row, f"tp_{i}") for i in range(*TP_RANGE)],
                )
                r_weight = min(tp_percentage / 20, 2) if tp_percentage >= 0.1 else 0.0
                weighted = round(r_weight, 2)
                trade = True if tp_percentage >= 0.1 else False
                highest_tp_column = f"{[getattr(row, f"tp_{i}") for i in range(*TP_RANGE)].index(tp_percentage) + 1}"

                with open(
                    f"data/algorithm_input-{till_date + timedelta(days=1)}-{strategy_type}.csv",
                    "a",
                    newline="",
                ) as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            row.hour,
                            "true" if trade else "false",
                            weighted if trade else None,
                            highest_tp_column if trade else None,
                        ]
                    )
