from datetime import datetime, timedelta
from decouple import config
import requests

from django.core.management.base import BaseCommand

from project.apps.core.models import Liquidation


COINALYZE_SECRET_API_KEY = config("COINALYZE_SECRET_API_KEY")
COINALYZE_LIQUIDATION_URL = "https://api.coinalyze.net/v1/liquidation-history"
FUTURE_MARKETS_URL = "https://api.coinalyze.net/v1/future-markets"

INTERVAL = "5min"


class Command(BaseCommand):
    help = "Loads inspections for the current day."

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
            "--interval",
            type=str,
            default=INTERVAL,
            help="Time interval for the data",
        )

    def get_params(self, **options) -> dict:
        """Returns the parameters for the request to the API"""
        now = datetime.now()
        return {
            "symbols": self.symbols,
            "from": int(
                datetime.timestamp(now - timedelta(days=options["from_days_ago"]))
            ),
            "to": int(datetime.timestamp(now - timedelta(days=options["to_days_ago"]))),
            "interval": options["interval"],
        }

    @property
    def symbols(self) -> list:
        """Returns the list of symbols to request data for"""
        symbols = []
        for market in requests.get(
            url=FUTURE_MARKETS_URL, headers={"api_key": COINALYZE_SECRET_API_KEY}
        ).json():
            if (symbol := market.get("symbol", "").upper()).startswith("BTCUSD"):
                symbols.append(symbol)
        return ",".join(symbols)

    def handle(self, *args, **options):
        for liquidation in requests.get(
            url=COINALYZE_LIQUIDATION_URL,
            headers={"api_key": COINALYZE_SECRET_API_KEY},
            params=self.get_params(**options),
        ).json():
            for history in liquidation.get("history"):
                if long := history.get("l"):
                    if long > 100:
                        print(Liquidation.objects.update_or_create(
                            symbol=liquidation["symbol"],
                            datetime=datetime.fromtimestamp(history["t"]),
                            side="LONG",
                            amount=long,
                            timeframe=options["interval"],
                        ))
                if short := history.get("s"):
                    if short > 100:
                        print(Liquidation.objects.update_or_create(
                            symbol=liquidation["symbol"],
                            datetime=datetime.fromtimestamp(history["t"]),
                            side="SHORT",
                            amount=short,
                            timeframe=options["interval"],
                        ))
