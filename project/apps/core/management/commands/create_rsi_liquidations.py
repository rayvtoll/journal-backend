from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import QuerySet

from project.apps.core.models import Position, OHLCV, RSILiquidation


def calculate_rsi(candles: list[OHLCV], period: int = 14) -> float:
    """Calculates the RSI for the given candles."""

    if not len(candles) > period:
        print("something went wrong")
        return 50

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
    return round(rsi, 2)


class Command(BaseCommand):
    help = "Creates Positions based on the current t-Ray-dingbot algorithm conditions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-days-ago",
            type=int,
            default=30,
            help="Number of days ago to start fetching data from",
        )
        parser.add_argument(
            "--to-days-ago",
            type=int,
            default=0,
            help="Number of days ago to stop fetching data",
        )

    def handle(self, *args, **options):
        now = datetime.now().replace(second=0, microsecond=0)
        for minutes_back in range(
            options["from_days_ago"] * 24 * 60, options["to_days_ago"] * 24 * 60 - 1, -1
        ):
            local_datetime = now - timedelta(days=1) - timedelta(minutes=minutes_back)
            rsi_candles = OHLCV.objects.filter(
                datetime__gte=local_datetime - timedelta(minutes=15),
                datetime__lte=local_datetime + timedelta(minutes=1),
                timeframe="1m",
                symbol="BTC/USDT:USDT",
            ).order_by("datetime")
            rsi_candles = list(rsi_candles)
            rsi = calculate_rsi(rsi_candles[:-1])
            if rsi <= 30 and rsi_candles[-1].close > rsi_candles[-2].high:
                print(
                    RSILiquidation.objects.update_or_create(
                        symbol="BTC/USDT:USDT",
                        datetime=local_datetime,
                        side="LONG",
                        rsi=rsi,
                        timeframe="1m",
                    )
                )
            elif rsi >= 70 and rsi_candles[-1].close < rsi_candles[-2].low:
                print(
                    RSILiquidation.objects.update_or_create(
                        symbol="BTC/USDT:USDT",
                        datetime=local_datetime,
                        side="SHORT",
                        rsi=rsi,
                        timeframe="1m",
                    )
                )
