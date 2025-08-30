from asyncio import run
from django.utils import timezone
from typing import List
from django.core.management.base import BaseCommand

from project.apps.core.models import OHLCV

from decouple import config
import ccxt.pro as ccxt

secret_key = config("BLOFIN_SECRET_KEY")
api_key = config("BLOFIN_API_KEY")
passphrase = config("BLOFIN_PASSPHRASE")

EXCHANGE = ccxt.binance()
# blofin(
# config={"apiKey": api_key, "secret": secret_key, "password": passphrase}
# )


async def get_closing_data() -> List[dict]:
    """Asynchronously fetches closing data for a given position."""

    candles = []
    for days in range(1, 200):
        candles = candles + await EXCHANGE.fetch_ohlcv(
            symbol="BTC/USDT:USDT",
            timeframe="5m",
            since=int((timezone.now() - timezone.timedelta(days=days + 1)).timestamp() * 1000),
            limit=288,
        )
    await EXCHANGE.close()
    return candles


class Command(BaseCommand):
    help = "Loads inspections for the current day."

    def handle(self, *args, **options):
        candles = run(get_closing_data())
        for candle in candles:
            ohlcv, _ = OHLCV.objects.update_or_create(
                defaults=dict(
                    symbol="BTC/USDT:USDT",
                    timeframe="5m",
                    datetime=timezone.datetime.fromtimestamp(candle[0] / 1000),
                ),
                open=candle[1],
                high=candle[2],
                low=candle[3],
                close=candle[4],
                volume=candle[5],
            )
            print(ohlcv)
        run(EXCHANGE.close())
