from datetime import datetime, timedelta
from decouple import config

from django.core.management.base import BaseCommand
from django.db import models

from project.apps.core.models import Position, OHLCV, Liquidation


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
        liquidations = Liquidation.objects.all()
        if options["from_days_ago"]:
            liquidations = liquidations.filter(
                datetime__gte=today - timedelta(days=options["from_days_ago"]),
            )
        if options["to_days_ago"]:
            liquidations = liquidations.filter(
                datetime__lte=today - timedelta(days=options["to_days_ago"])
            )
        liquidations = (
            liquidations.values("datetime")
            .annotate(
                total_amount=models.Sum("amount"),
                total_nr_of_liquidations=models.Count("id"),
                side=models.F("side"),
            )
            .order_by("datetime")
        )

        for liquidation in liquidations:

            # liquidation amount threshold
            if liquidation["total_amount"] < 100:
                continue

            # liquidation candle
            liquidation_candles = OHLCV.objects.filter(
                datetime=liquidation["datetime"], timeframe="5m"
            )
            if not liquidation_candles.first():
                continue
            liquidation_candle = liquidation_candles.first()

            # first candle after liquidation
            first_candles_after_liquidation = OHLCV.objects.filter(
                datetime__gte=liquidation["datetime"] + timedelta(minutes=5),
                datetime__lte=liquidation["datetime"] + timedelta(minutes=60),
                timeframe="5m",
            ).order_by("datetime")
            if not first_candles_after_liquidation.first():
                continue

            candles_before_entry = 0
            for i, candle in enumerate(first_candles_after_liquidation, start=1):
                if (
                    liquidation["side"] == "LONG"
                    and candle.close > liquidation_candle.high
                ):
                    confirmation_candle = candle
                    candles_before_entry = i
                    break
                if (
                    liquidation["side"] == "SHORT"
                    and candle.close < liquidation_candle.low
                ):
                    confirmation_candle = candle
                    candles_before_entry = i
                    break

            if not candles_before_entry:
                continue

            candles_after_liquidation = OHLCV.objects.filter(
                datetime__gt=confirmation_candle.datetime,
                timeframe="5m",
            ).order_by("datetime")
            for candle in candles_after_liquidation:
                if candle.close > confirmation_candle.close * 1.005:
                    print(
                        Position.objects.get_or_create(
                            liquidation_datetime=liquidation["datetime"],
                            start=candle.datetime + timedelta(minutes=5),
                            side=Position._PostionSideChoices.LONG,
                            amount=0.0001,
                            strategy_type=(
                                "live" if liquidation["side"] == "LONG" else "reversed"
                            ),
                            candles_before_entry=candles_before_entry,
                            liquidation_amount=liquidation["total_amount"],
                            nr_of_liquidations=liquidation["total_nr_of_liquidations"],
                            entry_price=candle.close * 0.9999,
                            timeframe="5m",
                        )
                    )
                    break
                if candle.close < confirmation_candle.close * 0.995:
                    print(
                        Position.objects.get_or_create(
                            liquidation_datetime=liquidation["datetime"],
                            start=candle.datetime + timedelta(minutes=5),
                            side=Position._PostionSideChoices.SHORT,
                            amount=0.0001,
                            strategy_type=(
                                "live" if liquidation["side"] == "SHORT" else "reversed"
                            ),
                            candles_before_entry=candles_before_entry,
                            liquidation_amount=liquidation["total_amount"],
                            nr_of_liquidations=liquidation["total_nr_of_liquidations"],
                            entry_price=candle.close * 1.0001,
                            timeframe="5m",
                        )
                    )
                    break
