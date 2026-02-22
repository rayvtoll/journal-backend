from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import QuerySet

from project.apps.core.models import Position, OHLCV, RSILiquidation


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

    def handle(self, *args, **options):
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        rsi_liquidations = (
            RSILiquidation.objects.filter(
                datetime__gte=now - timedelta(days=options["from_days_ago"]),
                datetime__lte=now - timedelta(days=options["to_days_ago"]),
                symbol="BTC/USDT:USDT",
                timeframe="1m",
            )
            .values("datetime", "side", "rsi")
            .annotate(
                nr_of_candles=models.Count("id"),
            )
            .order_by("datetime")
        )

        rsi_liquidations_5m = {}
        for liquidation in rsi_liquidations:
            datetime_5m = liquidation["datetime"].replace(
                minute=(liquidation["datetime"].minute // 5) * 5
            )
            key = (datetime_5m, liquidation["side"])
            if key not in rsi_liquidations_5m:
                rsi_liquidations_5m[key] = {
                    "datetime": datetime_5m,
                    "side": liquidation["side"],
                    "max_rsi": liquidation["rsi"],
                    "min_rsi": liquidation["rsi"],
                    "nr_of_candles": liquidation["nr_of_candles"],
                }
            else:
                rsi_liquidations_5m[key]["nr_of_candles"] += liquidation[
                    "nr_of_candles"
                ]
                min_rsi = min(rsi_liquidations_5m[key]["min_rsi"], liquidation["rsi"])
                rsi_liquidations_5m[key]["min_rsi"] = min_rsi
                max_rsi = max(rsi_liquidations_5m[key]["max_rsi"], liquidation["rsi"])
                rsi_liquidations_5m[key]["max_rsi"] = max_rsi

        # loop over rsi_liquidations_5m and create positions based on the number of candles with rsi <= 30 or rsi >= 70
        for liquidation in rsi_liquidations_5m.values():

            # filter out liquidations that are not extreme enough
            if (liquidation["side"] == "SHORT" and liquidation["max_rsi"] <= 80) or (
                liquidation["side"] == "LONG" and liquidation["min_rsi"] >= 20
            ):
                continue

            ohlcv_candles = OHLCV.objects.filter(
                datetime__gte=liquidation["datetime"],
                datetime__lte=liquidation["datetime"] + timedelta(minutes=20),
                symbol="BTC/USDT:USDT",
                timeframe="5m",
            ).order_by("datetime")

            if not ohlcv_candles.exists():
                continue

            ohlcv_candles = list(ohlcv_candles)
            liquidation_candle = ohlcv_candles[0]
            candles_after_liquidation = ohlcv_candles[1:]

            if not candles_after_liquidation:
                continue

            # TODO: check if volume increased on the candle of liquidation compared to the
            # previous candle, see if this works with rsi liquidations
            increased_volume = False
            if liquidation_candle.volume < candles_after_liquidation[0].volume:
                increased_volume = True

            if increased_volume:
                continue

            confirmation_candles = 0
            for i, candle in enumerate(candles_after_liquidation, start=1):
                if (
                    liquidation["side"] == "LONG"
                    and candle.close > liquidation_candle.high
                ):
                    confirmation_candle = candle
                    confirmation_candles = i
                    break
                elif (
                    liquidation["side"] == "SHORT"
                    and candle.close < liquidation_candle.low
                ):
                    confirmation_candle = candle
                    confirmation_candles = i
                    break

            if not confirmation_candles:
                continue

            candles_after_confirmation = OHLCV.objects.filter(
                datetime__gte=confirmation_candle.datetime,
                datetime__lte=confirmation_candle.datetime + timedelta(days=7),
                symbol="BTC/USDT:USDT",
                timeframe="5m",
            ).order_by("datetime")
            for candles_before_entry, candle in enumerate(
                candles_after_confirmation, start=1
            ):
                if candle.close > confirmation_candle.close * 1.004:
                    if liquidation["side"] == "LONG":
                        position, created = Position.objects.get_or_create(
                            liquidation_datetime=liquidation["datetime"],
                            start=candle.datetime + timedelta(minutes=5),
                            side=Position._PostionSideChoices.LONG,
                            amount=0.0001,
                            symbol="BTCUSDT",
                            strategy_type="rsi_reversed",
                            confirmation_candles=confirmation_candles,
                            candles_before_entry=candles_before_entry,
                            liquidation_amount=0,
                            nr_of_liquidations=liquidation["nr_of_candles"],
                            timeframe="5m",
                        )
                        position.entry_price = round(candle.close * 0.9999, 1)
                        position.save()
                        print(created, position)
                        break
                    break
                if candle.close < confirmation_candle.close * 0.996:
                    if liquidation["side"] == "LONG":
                        position, created = Position.objects.get_or_create(
                            liquidation_datetime=liquidation["datetime"],
                            start=candle.datetime + timedelta(minutes=5),
                            side=Position._PostionSideChoices.SHORT,
                            amount=0.0001,
                            symbol="BTCUSDT",
                            strategy_type="rsi_reversed",
                            confirmation_candles=confirmation_candles,
                            candles_before_entry=candles_before_entry,
                            liquidation_amount=0,
                            nr_of_liquidations=liquidation["nr_of_candles"],
                            timeframe="5m",
                        )
                        position.entry_price = round(candle.close * 1.0001, 1)
                        position.save()
                        print(created, position)
                        break
                    break
