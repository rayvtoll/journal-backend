from asyncio import run
from django.utils import timezone
from typing import List
from django.core.management.base import BaseCommand

from project.apps.core.models import OHLCV

import ccxt.pro as ccxt


EXCHANGE = ccxt.binance()


async def get_closing_data(
    timeframe: str = "5m", from_days_ago: int = 10, to_days_ago: int = 0
) -> List[dict]:
    """Asynchronously fetches closing data for a given position."""

    candles = []
    for days in range(from_days_ago, to_days_ago, -1):
        candles = candles + await EXCHANGE.fetch_ohlcv(
            symbol="BTC/USDT:USDT",
            timeframe=timeframe,
            since=int(
                (timezone.now() - timezone.timedelta(days=days)).timestamp() * 1000
            ),
            limit=int(24 * 60 / 5) if timeframe == "5m" else (24 * 60),
        )
    await EXCHANGE.close()
    return candles


class Command(BaseCommand):
    help = "Get OHLCV data and store it in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-days-ago",
            type=int,
            default=10,
            help="Number of days ago to start fetching data from",
        )
        parser.add_argument(
            "--to-days-ago",
            type=int,
            default=0,
            help="Number of days ago to stop fetching data",
        )
        parser.add_argument(
            "--timeframe",
            type=str,
            default="5m",
            help="Timeframe for the OHLCV data",
        )

    def handle(self, *args, **options):
        print(options)
        candles = run(
            get_closing_data(
                options["timeframe"], options["from_days_ago"], options["to_days_ago"]
            )
        )
        for candle in candles:
            candle_defaults = {
                "symbol": "BTC/USDT:USDT",
                "timeframe": options["timeframe"],
                "datetime": timezone.datetime.fromtimestamp(candle[0] / 1000),
            }
            try:
                ohlcv, created = OHLCV.objects.update_or_create(
                    defaults=candle_defaults,
                    open=candle[1],
                    high=candle[2],
                    low=candle[3],
                    close=candle[4],
                    volume=candle[5],
                )
                print(ohlcv, created)
            except Exception as e:
                ohlcv_s = OHLCV.objects.filter(**candle_defaults)
                if not ohlcv_s.exists():
                    print(f"Failed to create OHLCV: {e}")
                    continue
                ohlcv = ohlcv_s.first()
                ohlcv.open = candle[1]
                ohlcv.high = candle[2]
                ohlcv.low = candle[3]
                ohlcv.close = candle[4]
                ohlcv.volume = candle[5]
                ohlcv.save()
                print(f"Updated: {ohlcv} due to {e}")
        run(EXCHANGE.close())
