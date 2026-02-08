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
            default=1,
            help="Number of days ago to start fetching data from",
        )
        parser.add_argument(
            "--to-days-ago",
            type=int,
            default=0,
            help="Number of days ago to stop fetching data",
        )
        parser.add_argument(
            "--confirmation-distance",
            type=float,
            default=0.4,
            help="Distance for confirmation candle",
        )
        parser.add_argument(
            "--symbol",
            type=str,
            default="BTCUSD",
            help="Symbol for the data",
        )

    def handle(self, *args, **options):
        today = datetime.now().date()
        symbol_convertor = {
            "BTCUSD": "BTC/USDT:USDT",
            "ETHUSD": "ETH/USDT:USDT",
        }
        liquidations = Liquidation.objects.filter(symbol__startswith="BTCUSD")
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
                datetime__lt=liquidation["datetime"],
                timeframe="5m",
                symbol=symbol_convertor.get("BTCUSD"),
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
                datetime=liquidation["datetime"],
                timeframe="5m",
                symbol=symbol_convertor.get("BTCUSD"),
            )
            if not liquidation_candles.first():
                continue
            liquidation_candle = liquidation_candles.first()

            # candles around liquidation
            volume_candles_around_liquidation = OHLCV.objects.filter(
                symbol=symbol_convertor.get("BTCUSD"),
                datetime__gte=liquidation["datetime"] - timedelta(minutes=5),
                datetime__lte=liquidation["datetime"] + timedelta(minutes=10),
                timeframe="5m",
            ).order_by("datetime")
            if not volume_candles_around_liquidation.first():
                continue
            volume_candles_around_liquidation = [
                i for i in volume_candles_around_liquidation
            ]

            # check if volume increased on the candle of liquidation compared to the
            # previous candle
            increased_volume = False
            if (
                volume_candles_around_liquidation[0].volume
                < volume_candles_around_liquidation[1].volume
            ):
                increased_volume = True

            if not increased_volume:
                continue

            # first candle after liquidation
            first_candles_after_liquidation = volume_candles_around_liquidation[2:]

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
                symbol=symbol_convertor.get("BTCUSD"),
                datetime__gt=confirmation_candle.datetime,
                datetime__lte=confirmation_candle.datetime + timedelta(hours=24),
                timeframe="5m",
            ).order_by("datetime")
            for candles_before_entry, candle in enumerate(
                candles_after_liquidation, start=1
            ):
                if candle.close > confirmation_candle.close * (
                    1 + (options["confirmation_distance"]) / 100
                ):
                    if liquidation["side"] == "LONG":
                        break

                    position, created = Position.objects.get_or_create(
                        liquidation_datetime=liquidation["datetime"],
                        start=candle.datetime + timedelta(minutes=5),
                        side=Position._PostionSideChoices.LONG,
                        amount=0.0001,
                        symbol=options["symbol"] + "T",
                        strategy_type="reversed",
                        confirmation_candles=confirmation_candles,
                        candles_before_entry=candles_before_entry,
                        liquidation_amount=liquidation["total_amount"],
                        nr_of_liquidations=liquidation["total_nr_of_liquidations"],
                        timeframe="5m",
                    )
                    position.moving_average_50 = ma50
                    position.liquidation_closing_price = liquidation_candle.close
                    position.entry_price = round(candle.close * 0.9999, 1)
                    position.save()
                    print(created, position)
                    break
                if candle.close < confirmation_candle.close * (
                    1 - (options["confirmation_distance"]) / 100
                ):
                    if liquidation["side"] == "SHORT":
                        break

                    position, created = Position.objects.get_or_create(
                        liquidation_datetime=liquidation["datetime"],
                        start=candle.datetime + timedelta(minutes=5),
                        side=Position._PostionSideChoices.SHORT,
                        amount=0.0001,
                        symbol=options["symbol"] + "T",
                        strategy_type="reversed",
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
