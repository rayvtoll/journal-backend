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
    for days in range(10):
        candles = candles + await EXCHANGE.fetch_ohlcv(
            symbol="BTC/USDT:USDT",
            timeframe="5m",
            since=int(
                (timezone.now() - timezone.timedelta(days=days, hours=1)).timestamp()
                * 1000
            ),
            limit=288,
        )
    await EXCHANGE.close()
    return candles


class Command(BaseCommand):
    help = "Loads inspections for the current day."

    def handle(self, *args, **options):
        candles = run(get_closing_data())
        for candle in candles:
            candle_defaults = {
                "symbol": "BTC/USDT:USDT",
                "timeframe": "5m",
                "datetime": timezone.datetime.fromtimestamp(candle[0] / 1000),
            }
            try:
                ohlcv, _ = OHLCV.objects.update_or_create(
                    defaults=candle_defaults,
                    open=candle[1],
                    high=candle[2],
                    low=candle[3],
                    close=candle[4],
                    volume=candle[5],
                )
                print(ohlcv)
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
