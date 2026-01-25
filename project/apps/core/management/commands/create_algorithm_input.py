import csv
from datetime import timedelta
import pandas as pd
from typing import List

from django.core.management.base import BaseCommand
from django.db.models import QuerySet, Q
from django.utils import timezone

from project.apps.core.models import Position, OHLCV


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

    def run_algorithm_input(self, until_date: timezone.datetime, tp: int) -> List[dict]:
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
                    confirmation_candles__in=[1, 2, 3],
                )
                # .filter(
                #     Q(
                #         strategy_type="live",
                #         confirmation_candles=1,
                #     )
                #     | Q(
                #         strategy_type="reversed",
                #         confirmation_candles__in=[1, 2],
                #     )
                # )
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

            # nr of R's
            total_nr_of_r_s = round(
                (tp / sl * total_wins)  # win R's
                - (total_wins * 0.05)  # lost R's due to fees on wins
                - (total_losses)  # lost R's
                - (total_losses * 0.1),
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
                (total_nr_of_r_s + six_month_nr_of_r_s + three_month_nr_of_r_s) / 3,
                2,
            )
            return_row["trades"] = six_month_wins + six_month_losses
            return_row["trades"] = total_losses + total_wins
            return_list.append(return_row)
        return return_list

    def handle(self, *args, **options):
        # get until_date
        if options["year"] and options["month"]:
            year = options["year"]
            month = options["month"]
            first_of_month = timezone.datetime(year, month, 1)
            first_of_next_month = (first_of_month + timedelta(days=32)).replace(day=1)
            until_date = (first_of_next_month - timedelta(days=1)).date()
        else:
            until_date = timezone.now().date() - timedelta(days=1)

        day_dataframe = pd.DataFrame()
        for tp in range(1, 6):  # TP 1%-5%
            result = self.run_algorithm_input(until_date, tp)
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
        day_dataframe.to_csv(f"data/{until_date}.csv", index=False)

        # write csv header
        with open(
            f"data/{until_date + timedelta(days=1)}-algorithm_input.csv",
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

        df = pd.read_csv(f"data/{until_date}.csv")
        for row in df.itertuples(index=False):
            # select tp percentage column with the highest value and save the column name
            tp_percentage = max(
                [getattr(row, f"tp_{i}") for i in range(1, 6)],
            )

            # below 10 trades weighs less
            nr_of_trades_weighht = min((row.trades / 10) if row.trades else 0.0, 1.0)

            # below 10 R return weighs less
            r_weight = min(tp_percentage / 10, 1.0) if tp_percentage > 0.0 else 0.0

            # round to 2 decimal places
            weighted = round(min(nr_of_trades_weighht, r_weight), 2)

            trade = True if tp_percentage > 1 else False
            highest_tp_column = f"{[getattr(row, f"tp_{i}") for i in range(1, 6)].index(tp_percentage) + 1}"

            with open(
                f"data/{until_date + timedelta(days=1)}-algorithm_input.csv",
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
