from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import models

from project.apps.core.models import Position, OHLCV, Liquidation


class Command(BaseCommand):
    help = "Creates Positions based on the current t-Ray-dingbot algorithm conditions."

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

    def handle(self, *args, **options):
        for candle in (
            OHLCV.objects.filter(
                datetime__gte=datetime.now() - timedelta(days=options["from_days_ago"]),
                datetime__lte=datetime.now() - timedelta(days=options["to_days_ago"]),
                timeframe="5m",
            )
            .distinct()
            .order_by("datetime")
        ):
            previous_candle = None
            previous_candles = OHLCV.objects.filter(
                datetime__lt=candle.datetime,
                datetime__gte=candle.datetime - timedelta(minutes=10),
                timeframe="5m",
            ).order_by("-datetime")[:1]

            if not previous_candles.exists():
                continue
            else:
                previous_candle = previous_candles.first()

            if candle.close > previous_candle.high:
                long_liquidations = Liquidation.objects.filter(
                    datetime=previous_candle.datetime,
                    side="LONG",
                    timeframe="5min",
                )
                total_long_liquidation_amount = long_liquidations.aggregate(
                    total_amount=models.Sum("amount")
                )
                total_long_liquidation_amount = (
                    total_long_liquidation_amount.get("total_amount")
                    if total_long_liquidation_amount.get("total_amount")
                    else 0
                )

                if total_long_liquidation_amount > 100_000 or (
                    total_long_liquidation_amount > 10_000
                    and len(long_liquidations) >= 3
                ):
                    if Position.objects.filter(
                        start=candle.datetime + timedelta(minutes=5)
                    ).exists():
                        print(
                            f"Position for {candle.datetime + timedelta(minutes=5)} already exists, skipping."
                        )
                    else:
                        print(
                            Position.objects.create(
                                start=candle.datetime + timedelta(minutes=5),
                                side=Position._PostionSideChoices.LONG,
                                amount=0.0001,
                                strategy_type="journaling",
                                candles_before_entry=1,
                                liquidation_amount=total_long_liquidation_amount,
                                nr_of_liquidations=len(long_liquidations),
                                entry_price=candle.close,
                                timeframe="5m",
                            )
                        )

            if candle.close < previous_candle.low:
                short_liquidations = Liquidation.objects.filter(
                    datetime=previous_candle.datetime,
                    side="SHORT",
                    timeframe="5min",
                )
                total_short_liquidation_amount = short_liquidations.aggregate(
                    total_amount=models.Sum("amount")
                )
                total_short_liquidation_amount = (
                    total_short_liquidation_amount.get("total_amount")
                    if total_short_liquidation_amount.get("total_amount")
                    else 0
                )

                if total_short_liquidation_amount > 100_000 or (
                    total_short_liquidation_amount > 10_000
                    and len(short_liquidations) >= 3
                ):
                    if Position.objects.filter(
                        start=candle.datetime + timedelta(minutes=5)
                    ).exists():
                        print(
                            f"Position for {candle.datetime + timedelta(minutes=5)} already exists, skipping."
                        )
                    else:
                        print(
                            Position.objects.create(
                                start=candle.datetime + timedelta(minutes=5),
                                side=Position._PostionSideChoices.SHORT,
                                amount=0.0001,
                                strategy_type="journaling",
                                candles_before_entry=1,
                                liquidation_amount=total_short_liquidation_amount,
                                nr_of_liquidations=len(short_liquidations),
                                entry_price=candle.close,
                                timeframe="5m",
                            )
                        )
