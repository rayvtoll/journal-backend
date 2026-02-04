import csv
from datetime import date
from django.conf import settings
import pandas as pd
from typing import List

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils import timezone

from project.apps.core.models import Position, OHLCV


x10_TP_SL_PAIRS = [
    # 5R pairs
    (30, 6),
    (40, 8),
    (50, 10),
    (60, 12),
    (70, 14),
]


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

    def calculate_position_outcome(
        self,
        position: Position,
        tp: float,
        sl: float,
        until_date: date,
    ) -> tuple[int, int, int, int, int, int]:
        total_wins = 0
        total_losses = 0
        six_month_wins = 0
        six_month_losses = 0
        three_month_wins = 0
        three_month_losses = 0

        position.what_if_returns = 0
        last_candle = min(
            position.start + timezone.timedelta(days=14),
            timezone.datetime(until_date.year, until_date.month, until_date.day),
        )
        cache_key = f"p{position.id}-{position.strategy_type}-l{last_candle.strftime('%Y%m%d')}-tp{int(tp * 10)}-sl{int(sl * 10)}"
        if response_tuple := cache.get(cache_key):
            return response_tuple
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
                        if until_date - position.liquidation_datetime.date()
                        <= timezone.timedelta(days=180)
                        else 0
                    )
                    three_month_losses += (
                        1
                        if until_date - position.liquidation_datetime.date()
                        <= timezone.timedelta(days=90)
                        else 0
                    )
                    break

                # TP
                if candle.close >= entry_price + (entry_price * tp / 100):
                    total_wins += 1
                    six_month_wins += (
                        1
                        if until_date - position.liquidation_datetime.date()
                        <= timezone.timedelta(days=180)
                        else 0
                    )
                    three_month_wins += (
                        1
                        if until_date - position.liquidation_datetime.date()
                        <= timezone.timedelta(days=90)
                        else 0
                    )
                    break

            if position.side == "SHORT":

                # SL
                if candle.high >= entry_price + (entry_price * sl / 100):
                    total_losses += 1
                    six_month_losses += (
                        1
                        if until_date - position.liquidation_datetime.date()
                        <= timezone.timedelta(days=180)
                        else 0
                    )
                    three_month_losses += (
                        1
                        if until_date - position.liquidation_datetime.date()
                        <= timezone.timedelta(days=90)
                        else 0
                    )
                    break

                # TP
                if candle.close <= entry_price - (entry_price * tp / 100):
                    total_wins += 1
                    six_month_wins += (
                        1
                        if until_date - position.liquidation_datetime.date()
                        <= timezone.timedelta(days=180)
                        else 0
                    )
                    three_month_wins += (
                        1
                        if until_date - position.liquidation_datetime.date()
                        <= timezone.timedelta(days=90)
                        else 0
                    )
                    break
        return_tuple = (
            total_wins,
            total_losses,
            six_month_wins,
            six_month_losses,
            three_month_wins,
            three_month_losses,
        )
        cache.set(key=cache_key, value=return_tuple)
        return return_tuple

    def run_algorithm_input(
        self,
        until_date: date,
        tpx10: int,
        slx10: int,
        strategy_type: str,
        **filter_kwargs,
    ) -> List[dict]:
        sl: float = slx10 / 10
        tp: float = tpx10 / 10
        return_list: List[dict] = []
        for hour in range(24):
            # for hour in [2, 3, 4, 14, 15, 16]:
            return_row: dict = {"hour": hour}
            positions: QuerySet[Position] = (
                Position.objects.filter(
                    liquidation_amount__gte=2000,
                    timeframe="5m",
                    start__gte=until_date
                    - timezone.timedelta(
                        days=int(
                            180
                        ),  # int(365 / 2) gives highers results than int(365 / 4), why?
                    ),  # last 6 months # TODO: something goes wrong here
                    start__lt=until_date,
                    liquidation_datetime__hour=hour,
                    liquidation_datetime__week_day__in=[2, 3, 4, 5, 6],  # monday-friday
                    strategy_type=strategy_type,
                    **filter_kwargs,
                )
                .exclude(candles_before_entry=1)
                .distinct()
                .order_by("liquidation_datetime")
            )

            total_wins = 0
            total_losses = 0
            six_month_wins = 0
            six_month_losses = 0
            three_month_wins = 0
            three_month_losses = 0
            for position in positions:
                (
                    local_total_wins,
                    local_total_losses,
                    local_six_month_wins,
                    local_six_month_losses,
                    local_three_month_wins,
                    local_three_month_losses,
                ) = self.calculate_position_outcome(position, tp, sl, until_date)
                total_wins += local_total_wins
                total_losses += local_total_losses
                six_month_wins += local_six_month_wins
                six_month_losses += local_six_month_losses
                three_month_wins += local_three_month_wins
                three_month_losses += local_three_month_losses

            # nr of R's
            # total_nr_of_r_s = round(
            #     (tp / sl * total_wins)  # win R's
            #     - (total_wins * 0.05)  # lost R's due to fees on wins
            #     - (total_losses)  # lost R's
            #     - (total_losses * 0.1),  # lost R's due to fees on losses
            #     2,
            # )
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
            return_row[f"tpx10_{tpx10}_slx10_{slx10}"] = round(
                (
                    # total_nr_of_r_s +
                    (six_month_nr_of_r_s * 2)
                    + (three_month_nr_of_r_s * 4)
                )
                / 2,
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
            till_date = timezone.now().date()

        print(f"Generating algorithm input data for {till_date}")

        for strategy_type in ["live", "reversed"]:
            day_dataframe = pd.DataFrame()
            if strategy_type == "live":
                filter_kwargs = {"confirmation_candles": 1}
            else:
                filter_kwargs = {"confirmation_candles__in": [1, 2]}
            for tpx10, slx10 in x10_TP_SL_PAIRS:
                result = self.run_algorithm_input(
                    till_date, tpx10, slx10, strategy_type, **filter_kwargs
                )
                print(f"Completed TP {tpx10 / 10} SL {slx10 / 10} for {strategy_type}")
                tp_dataframe = pd.DataFrame(result)
                if day_dataframe.empty:
                    day_dataframe = tp_dataframe[
                        ["hour", "trades", f"tpx10_{tpx10}_slx10_{slx10}"]
                    ]
                else:
                    day_dataframe = pd.merge(
                        day_dataframe,
                        tp_dataframe[["hour", f"tpx10_{tpx10}_slx10_{slx10}"]],
                        on="hour",
                    )
            # write to csv
            day_dataframe.to_csv(
                f"{settings.ALGORITHM_EXPORT_PATH}/data-{till_date}-{strategy_type}.csv",
                index=False,
            )
            print(f"Data for {till_date} - {strategy_type}:")
            print(day_dataframe)

            # write csv header
            with open(
                f"{settings.ALGORITHM_EXPORT_PATH}/algorithm_input-{till_date}-{strategy_type}.csv",
                "w",
                newline="",
            ) as f:
                writer = csv.writer(f)
                header_row = [
                    "hour",
                    "trade",
                    "weight",
                    "tp",
                    "sl",
                ]
                print(f"Header for {strategy_type}:")
                print("\t".join(header_row))
                writer.writerow(header_row)

            df = pd.read_csv(
                f"{settings.ALGORITHM_EXPORT_PATH}/data-{till_date}-{strategy_type}.csv"
            )
            for row in df.itertuples(index=False):
                tp_percentage = max(
                    [getattr(row, f"tpx10_{i}_slx10_{j}") for i, j in x10_TP_SL_PAIRS],
                )
                r_weight = tp_percentage / 20 if tp_percentage >= 0.1 else 0.0
                if r_weight >= 1.0:
                    r_weight = r_weight * 0.5 + 0.5
                weighted = round(min(r_weight / 2, 1.0), 2)
                trade = True if tp_percentage >= 0.1 else False
                highest_sl_value: int = 0
                highest_tp_value: int = 0
                highest_score = -float("inf")
                for i, j in x10_TP_SL_PAIRS:
                    current_value = getattr(row, f"tpx10_{i}_slx10_{j}")
                    if current_value > highest_score:
                        highest_score = current_value
                        highest_tp_value = i / 10
                        highest_sl_value = j / 10
                with open(
                    f"{settings.ALGORITHM_EXPORT_PATH}/algorithm_input-{till_date}-{strategy_type}.csv",
                    "a",
                    newline="",
                ) as f:
                    writer = csv.writer(f)
                    write_row = [
                        row.hour,
                        "true" if trade else "false",
                        weighted if trade else None,
                        highest_tp_value if trade else None,
                        highest_sl_value if trade else None,
                    ]
                    print("\t".join(map(str, write_row)))
                    writer.writerow(write_row)
