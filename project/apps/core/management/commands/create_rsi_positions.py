from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import QuerySet

from project.apps.core.models import Position, OHLCV


def calculate_rsi(candles: list[OHLCV], period: int = 14) -> float:
    """Calculates the RSI for the given candles."""

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = candles[-i].close - candles[-i - 1].close
        if change > 0:
            gains += change
        else:
            losses -= change
    if losses == 0:
        return 100.0
    rs = gains / losses
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


class Command(BaseCommand):
    help = "Creates Positions based on the current t-Ray-dingbot algorithm conditions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-days-ago",
            type=int,
            default=0,
            help="Number of days ago to start fetching data from",
        )
        parser.add_argument(
            "--to-days-ago",
            type=int,
            default=0,
            help="Number of days ago to stop fetching data",
        )

    def handle(self, *args, **options):
        today = datetime.now().date()
        starting_date = today - timedelta(days=options["from_days_ago"])
        candles: QuerySet[OHLCV] = OHLCV.objects.filter(
            datetime__gte=starting_date - timedelta(days=30),
            datetime__lt=today - timedelta(days=options["to_days_ago"]),
        )
        rsi_candles: list[OHLCV] = []

        for candle in candles.order_by("datetime"):

            # Need at least 14 candles to calculate RSI
            if len(rsi_candles) < 16:
                rsi_candles.append(candle)
                continue

            # Calculate RSI
            rsi_candles = rsi_candles[-16:]
            rsi = calculate_rsi(rsi_candles[-16:])

            # Check for RSI overbought/oversold conditions
            if 70 >= rsi >= 30:
                rsi_candles.append(candle)
                continue

            # Single confirming candle
            if (
                rsi >= 70
                # and rsi_candles[-1].high < rsi_candles[-2].high
                and rsi_candles[-1].close < rsi_candles[-2].low
                and rsi_candles[-3].high < rsi_candles[-2].high
            ) or (
                rsi <= 30
                # and rsi_candles[-1].low > rsi_candles[-2].low
                and rsi_candles[-1].close > rsi_candles[-2].high
                and rsi_candles[-2].low < rsi_candles[-3].low
            ):
                confirmation_candles = 1

            # Double confirming candle
            elif (
                rsi >= 70
                # and rsi_candles[-1].high < rsi_candles[-2].high
                and candle.close < rsi_candles[-2].low
                and rsi_candles[-2].high > rsi_candles[-3].high
            ) or (
                rsi <= 30
                # and rsi_candles[-1].low > rsi_candles[-2].low
                and candle.close > rsi_candles[-2].high
                and rsi_candles[-2].low < rsi_candles[-3].low
            ):
                confirmation_candles = 2

            else:
                rsi_candles.append(candle)
                continue

            before_entering_candles = OHLCV.objects.filter(
                datetime__gt=rsi_candles[-2].datetime
                + timedelta(minutes=5 * confirmation_candles),
                timeframe="5m",
            ).order_by("datetime")
            for candles_before_entry, entering_candle in enumerate(
                before_entering_candles, start=1
            ):
                if (
                    entering_candle.close
                    > (
                        candle.close
                        if confirmation_candles == 2
                        else rsi_candles[-1].close
                    )
                    * 1.005
                ):
                    print(
                        Position.objects.get_or_create(
                            liquidation_datetime=rsi_candles[-2].datetime,
                            start=entering_candle.datetime + timedelta(minutes=5),
                            side=Position._PostionSideChoices.LONG,
                            amount=0.0001,
                            strategy_type=("rsi_live" if rsi <= 30 else "rsi_reversed"),
                            confirmation_candles=confirmation_candles,
                            candles_before_entry=candles_before_entry,
                            liquidation_amount=0,
                            nr_of_liquidations=0,
                            entry_price=candle.close * 0.9999,
                            timeframe="5m",
                        )
                    )
                    break
                if (
                    entering_candle.close
                    < (
                        candle.close
                        if confirmation_candles == 2
                        else rsi_candles[-1].close
                    )
                    * 0.995
                ):
                    print(
                        Position.objects.get_or_create(
                            liquidation_datetime=rsi_candles[-2].datetime,
                            start=entering_candle.datetime + timedelta(minutes=5),
                            side=Position._PostionSideChoices.SHORT,
                            amount=0.0001,
                            strategy_type=("rsi_live" if rsi >= 70 else "rsi_reversed"),
                            confirmation_candles=confirmation_candles,
                            candles_before_entry=candles_before_entry,
                            liquidation_amount=0,
                            nr_of_liquidations=0,
                            entry_price=candle.close * 1.0001,
                            timeframe="5m",
                        )
                    )
                    break
            rsi_candles.append(candle)
