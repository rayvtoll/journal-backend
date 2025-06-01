from asyncio import run
from datetime import datetime, timedelta
from typing import List
from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from project.apps.core.models import Position

from decouple import config
import ccxt.pro as ccxt

secret_key = config("BLOFIN_SECRET_KEY")
api_key = config("BLOFIN_API_KEY")
passphrase = config("BLOFIN_PASSPHRASE")

EXCHANGE = ccxt.blofin(
    config={"apiKey": api_key, "secret": secret_key, "password": passphrase}
)


async def get_closing_data() -> List[dict]:
    """Asynchronously fetches closing data for a given position."""

    return await EXCHANGE.fetch_closed_orders(
        "BTC/USDT:USDT",
        since=int((datetime.now() - timedelta(days=60)).timestamp() * 1000),
        params={"tpsl": True},
        limit=1000,
    )


class Command(BaseCommand):
    help = "Loads inspections for the current day."

    def handle(self, *args, **options):
        closed_orders = run(get_closing_data())
        positions: QuerySet[Position] = Position.objects.filter(end=None)
        for position in positions:
            for closed_order in closed_orders:
                if not (
                    closed_order.get("info", {}).get("triggerType", "") == "sl"
                    or closed_order.get("info", {}).get("triggerType", "") == "tp"
                ):
                    continue
                if not (
                    round(position.take_profit_price, 1)
                    == round(closed_order.get("takeProfitTriggerPrice", 0.0), 1)
                ):
                    continue
                if (
                    round(position.amount, 1)
                    == round(closed_order.get("amount", 0.0), 1)
                ):
                    position.end = datetime.fromtimestamp(
                        closed_order["timestamp"] / 1000
                    )
                    match closed_order.get("info", {}).get("triggerType", ""):
                        case "sl":
                            position.closing_price = closed_order.get(
                                "slTriggerPrice", 0.0
                            )
                        case "tp":
                            position.closing_price = closed_order.get(
                                "tpTriggerPrice", 0.0
                            )

                    position.save()
