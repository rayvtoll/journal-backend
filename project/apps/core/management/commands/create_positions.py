from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import models

from project.apps.core.models import Position, OHLCV, Liquidation


def calculate_rsi(candles: list[OHLCV], period: int = 14) -> float:
    """Calculates the RSI for the given candles."""

    if not len(candles) > period:
        print("something went wrong")
        return 50

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = candles[-i].close - candles[-i - 1].close
        if change > 0:
            gains += change
        else:
            losses -= change
    if losses == 0:
        return 100.0
    rs = gains / losses
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)


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

            # RSI calculation
            rsi_candles = OHLCV.objects.filter(
                datetime__gte=liquidation["datetime"] - timedelta(minutes=5 * 14),
                datetime__lte=liquidation["datetime"],
                timeframe="5m",
                symbol=symbol_convertor.get("BTCUSD"),
            ).order_by("datetime")
            rsi_candles = list(rsi_candles)
            liquidation_rsi = calculate_rsi(rsi_candles)

            # ATR calculation
            atr_values = []
            for i in range(1, len(rsi_candles)):
                current_candle = rsi_candles[i]
                previous_candle = rsi_candles[i - 1]
                tr = max(
                    current_candle.high - current_candle.low,
                    abs(current_candle.high - previous_candle.close),
                    abs(current_candle.low - previous_candle.close),
                )
                atr_values.append(tr)
            atr = (
                sum(atr_values) / len(atr_values) / rsi_candles[-1].close * 100
                if atr_values
                else 0
            )

            # candles around liquidation
            volume_candles_around_liquidation = OHLCV.objects.filter(
                symbol=symbol_convertor.get("BTCUSD"),
                datetime__gte=liquidation["datetime"] - timedelta(minutes=5),
                datetime__lte=liquidation["datetime"] + timedelta(minutes=10),
                timeframe="5m",
            ).order_by("datetime")
            if not volume_candles_around_liquidation.first():
                continue
            volume_candles_around_liquidation = list(volume_candles_around_liquidation)

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
                datetime__lte=confirmation_candle.datetime + timedelta(days=7),
                timeframe="5m",
            ).order_by("datetime")
            for candles_before_entry, candle in enumerate(
                candles_after_liquidation, start=1
            ):
                if candle.close > confirmation_candle.close * (
                    1 + (options["confirmation_distance"]) / 100
                ):
                    # if liquidation["side"] == "LONG" and confirmation_candles == 1:
                    #     position, created = Position.objects.get_or_create(
                    #         liquidation_datetime=liquidation["datetime"],
                    #         start=candle.datetime + timedelta(minutes=5),
                    #         side=Position._PostionSideChoices.LONG,
                    #         amount=0.0001,
                    #         symbol=options["symbol"] + "T",
                    #         strategy_type="live",
                    #         confirmation_candles=confirmation_candles,
                    #         candles_before_entry=candles_before_entry,
                    #         liquidation_amount=liquidation["total_amount"],
                    #         nr_of_liquidations=liquidation["total_nr_of_liquidations"],
                    #         timeframe="5m",
                    #         liquidation_candle=liquidation_candle,
                    #         liquidation_rsi=liquidation_rsi,
                    #         liquidation_atr=atr,
                    #     )
                    #     print(created, position)
                    #     break

                    if liquidation["side"] == "SHORT":
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
                            liquidation_candle=liquidation_candle,
                            liquidation_rsi=liquidation_rsi,
                            liquidation_atr=atr,
                        )
                        print(created, position)
                        break
                    break
                if candle.close < confirmation_candle.close * (
                    1 - (options["confirmation_distance"]) / 100
                ):
                    # if liquidation["side"] == "SHORT" and confirmation_candles == 1:
                    #     position, created = Position.objects.get_or_create(
                    #         liquidation_datetime=liquidation["datetime"],
                    #         start=candle.datetime + timedelta(minutes=5),
                    #         side=Position._PostionSideChoices.SHORT,
                    #         amount=0.0001,
                    #         symbol=options["symbol"] + "T",
                    #         strategy_type="live",
                    #         confirmation_candles=confirmation_candles,
                    #         candles_before_entry=candles_before_entry,
                    #         liquidation_amount=liquidation["total_amount"],
                    #         nr_of_liquidations=liquidation["total_nr_of_liquidations"],
                    #         timeframe="5m",
                    #         liquidation_candle=liquidation_candle,
                    #         liquidation_rsi=liquidation_rsi,
                    #         liquidation_atr=atr,
                    #     )
                    #     print(created, position)
                    #     break

                    if liquidation["side"] == "LONG":
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
                            liquidation_candle=liquidation_candle,
                            liquidation_rsi=liquidation_rsi,
                            liquidation_atr=atr,
                        )
                        print(created, position)
                        break
                    break
