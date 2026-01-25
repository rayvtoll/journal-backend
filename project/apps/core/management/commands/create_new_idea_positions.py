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
            # calculate 50 moving average value at liquidation time
            candles_for_ma50 = OHLCV.objects.filter(
                datetime__lt=liquidation["datetime"], timeframe="5m"
            ).order_by("-datetime")[:50]
            if len(candles_for_ma50) == 50:
                ma50 = round(sum(candle.close for candle in candles_for_ma50) / 50, 1)
            else:
                ma50 = None

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

            confirmation_candles = 0
            for i, candle in enumerate(first_candles_after_liquidation, start=1):
                if (
                    liquidation["side"] == "LONG"
                    and candle.close > liquidation_candle.high
                ):
                    confirmation_candle = candle
                    confirmation_candles = i
                    break
                if (
                    liquidation["side"] == "SHORT"
                    and candle.close < liquidation_candle.low
                ):
                    confirmation_candle = candle
                    confirmation_candles = i
                    break

            if not confirmation_candles:
                continue

            candles_after_liquidation = OHLCV.objects.filter(
                datetime__gt=confirmation_candle.datetime,
                timeframe="5m",
            ).order_by("datetime")
            for candles_before_entry, candle in enumerate(
                candles_after_liquidation, start=1
            ):
                if candle.close > confirmation_candle.close * 1.005:
                    position, created = Position.objects.get_or_create(
                        liquidation_datetime=liquidation["datetime"],
                        start=candle.datetime + timedelta(minutes=5),
                        side=Position._PostionSideChoices.LONG,
                        amount=0.0001,
                        strategy_type=(
                            "live" if liquidation["side"] == "LONG" else "reversed"
                        ),
                        confirmation_candles=confirmation_candles,
                        candles_before_entry=candles_before_entry,
                        liquidation_amount=liquidation["total_amount"],
                        nr_of_liquidations=liquidation["total_nr_of_liquidations"],
                        timeframe="5m",
                    )
                    position.moving_average_50 = ma50
                    position.liquidation_closing_price = liquidation_candle.close
                    position.entry_price = round(candle.close * 1.0001, 1)
                    position.save()
                    print(created, position)
                    break
                if candle.close < confirmation_candle.close * 0.995:

                    position, created = Position.objects.get_or_create(
                        liquidation_datetime=liquidation["datetime"],
                        start=candle.datetime + timedelta(minutes=5),
                        side=Position._PostionSideChoices.SHORT,
                        amount=0.0001,
                        strategy_type=(
                            "live" if liquidation["side"] == "SHORT" else "reversed"
                        ),
                        confirmation_candles=confirmation_candles,
                        candles_before_entry=candles_before_entry,
                        liquidation_amount=liquidation["total_amount"],
                        nr_of_liquidations=liquidation["total_nr_of_liquidations"],
                        timeframe="5m",
                    )
                    position.moving_average_50 = ma50
                    position.liquidation_closing_price = liquidation_candle.close
                    position.entry_price = round(candle.close * 1.0001, 1)
                    position.save()
                    print(created, position)
                    break
