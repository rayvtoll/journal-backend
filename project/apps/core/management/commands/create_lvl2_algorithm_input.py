from dataclasses import dataclass
from datetime import date
from decouple import config
import discord
import pandas as pd
from typing import List

from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils import timezone

from project.apps.core.models import Position, OHLCV


INITIAL_CAPITAL = 100

BLOFIN_MARKET_ORDER_FEE = 0.06 / 100  # 0.06% for non VIP users
BLOFIN_LIMIT_ORDER_FEE = 0.02 / 100  # 0.002% for non VIP users

USE_DISCORD = config("USE_DISCORD", cast=bool, default=False)
if USE_DISCORD:
    DISCORD_CHANNEL_WAITING_ID = config("DISCORD_CHANNEL_WAITING_ID", cast=int)
    DISCORD_PRIVATE_KEY = config("DISCORD_PRIVATE_KEY")
    USE_AT_EVERYONE = config("USE_AT_EVERYONE", cast=bool, default="false")


@dataclass
class DiscordMessage:
    """DiscordMessage class to hold the discord message data"""

    channel_id: str
    messages: List[str]
    at_everyone: bool = False


def post_to_discord(discord_message: DiscordMessage) -> None:
    """Post messages to discord and empty the message queue"""

    if not USE_DISCORD:
        return

    intents = discord.Intents.default()
    intents.messages = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            channel = client.get_channel(discord_message.channel_id)
            if discord_message.at_everyone:
                await channel.send(f"@everyone\n")
            for message in discord_message.messages:
                await channel.send(f"{message}")
        except Exception as e:
            print(f"Failed to post to Discord: {e}")
        finally:
            await client.close()

    try:
        client.run(token=DISCORD_PRIVATE_KEY, log_handler=None)
    except Exception as e:
        print(f"Failed to post to Discord: {e}")


class Command(BaseCommand):
    help = "Get input data for algorithm."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            help="year for which to create the algorithm input data",
        )
        parser.add_argument(
            "--month",
            type=int,
            help="month for which to create the algorithm input data",
        )
        parser.add_argument(
            "--day",
            type=int,
            help="day for which to create the algorithm input data",
            default=1,
        )
        parser.add_argument(
            "--symbol",
            type=str,
            help="symbol for which to create the algorithm input data",
            default="BTC",
        )

    def handle(self, *args, **options):
        if options["year"] and options["month"] and options["day"]:
            year = options["year"]
            month = options["month"]
            day = options["day"]
            till_date = date(year, month, day)
        else:
            till_date = timezone.now().date()

        symbol = options["symbol"] + "USDT"
        symbol_convertor = {
            "BTCUSDT": "BTC/USDT:USDT",
            "ETHUSDT": "ETH/USDT:USDT",
        }
        strategy_type = "reversed"
        positions: QuerySet[Position] = Position.objects.exclude(
            candles_before_entry=1,
        )
        positions = positions.filter(
            symbol=symbol,
            confirmation_candles__in=[1, 2],
            strategy_type=strategy_type,
            liquidation_datetime__week_day__in=[2, 3, 4, 5, 6],  # monday-friday
            liquidation_datetime__date__lt=till_date,
            liquidation_datetime__gte=till_date - timezone.timedelta(days=90),
            timeframe="5m",
            liquidation_amount__gte=2000,
        ).distinct()

        performance_list: List[dict] = []

        for hour in range(24):
            total_returns = INITIAL_CAPITAL
            hour_row: dict = {"hour": hour}
            hour_positions = positions.filter(liquidation_datetime__hour=hour).order_by(
                "liquidation_datetime"
            )
            for position in hour_positions:
                try:
                    try:
                        # try the file of the liquidation date first
                        algorithm_input: pd.DataFrame = pd.read_csv(
                            f"data/algorithm_input-{position.symbol}-{position.liquidation_datetime.date()}-{position.strategy_type}.csv"
                        )
                    except:
                        # if not found, try the file of the Monday of that week
                        algorithm_input: pd.DataFrame = pd.read_csv(
                            f"data/algorithm_input-{position.symbol}-{position.liquidation_datetime.date() - timezone.timedelta(days=position.liquidation_datetime.weekday())}-{position.strategy_type}.csv"
                        )
                except:
                    # if not found, skip this position
                    continue
                trade: bool = False
                tp: float = 0.0
                sl: float = 0.0
                performance_lvl1: float
                for row in algorithm_input.itertuples():
                    if row.hour == hour:
                        trade, performance_lvl1, tp, sl = (
                            row.trade_lvl1,
                            row.performance_lvl1,
                            row.tp,
                            row.sl,
                        )

                if not trade:
                    continue

                position.what_if_returns = 0
                position.start = position.start.replace(second=0, microsecond=0)
                ohlcv_s = OHLCV.objects.filter(
                    symbol=symbol_convertor.get(position.symbol),
                    datetime__gte=position.start,
                    datetime__lt=min(
                        position.start.date() + timezone.timedelta(days=28), till_date
                    ),
                    timeframe="5m",
                ).order_by("datetime")
                if ohlcv_s.exists():
                    position.entry_price = round(
                        (
                            ohlcv_s.first().open * 1.0001
                            if position.side == "SHORT"
                            else ohlcv_s.first().open * 0.9999
                        ),
                        1,
                    )
                    position.amount = round(
                        (total_returns)
                        / sl
                        / position.entry_price
                        * min(performance_lvl1 / 10, 1),
                        4,
                    )
                    amount = position.amount
                    fees_for_opening = (
                        position.amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                    )
                    position.what_if_returns -= fees_for_opening

                for candle in ohlcv_s:

                    if position.side == "LONG":

                        # SL
                        if candle.low <= position.entry_price - (
                            position.entry_price * sl / 100
                        ):
                            position.closing_price = round(
                                position.entry_price
                                - (position.entry_price * sl / 100),
                                1,
                            )
                            fees_for_closing = (
                                amount
                                * position.closing_price
                                * BLOFIN_MARKET_ORDER_FEE
                            )
                            position.what_if_returns -= fees_for_closing
                            loss = (position.entry_price * sl / 100) * amount
                            position.what_if_returns -= loss
                            total_returns += position.what_if_returns
                            break

                        # final TP
                        if candle.high >= position.entry_price + (
                            position.entry_price * tp / 100
                        ):
                            position.closing_price = round(
                                position.entry_price
                                + (position.entry_price * tp / 100),
                                1,
                            )
                            fees_for_closing = (
                                amount * position.entry_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            position.what_if_returns -= fees_for_closing
                            local_win = (position.entry_price * tp / 100) * amount
                            position.what_if_returns += local_win
                            total_returns += position.what_if_returns
                            break

                    if position.side == "SHORT":

                        # SL
                        if candle.high >= position.entry_price + (
                            position.entry_price * sl / 100
                        ):
                            position.closing_price = round(
                                position.entry_price
                                + (position.entry_price * sl / 100),
                                1,
                            )
                            fees_for_closing = (
                                amount
                                * position.closing_price
                                * BLOFIN_MARKET_ORDER_FEE
                            )
                            position.what_if_returns -= fees_for_closing
                            loss = (position.entry_price * sl / 100) * amount
                            position.what_if_returns -= loss
                            total_returns += position.what_if_returns
                            break

                        # final TP
                        if candle.low <= position.entry_price - (
                            position.entry_price * tp / 100
                        ):
                            position.closing_price = round(
                                position.entry_price
                                - (position.entry_price * tp / 100),
                                1,
                            )
                            fees_for_closing = (
                                amount * position.closing_price * BLOFIN_LIMIT_ORDER_FEE
                            )
                            position.what_if_returns -= fees_for_closing
                            local_wins = (position.entry_price * tp / 100) * amount
                            position.what_if_returns += local_wins
                            total_returns += position.what_if_returns
                            break
            hour_row["performance_lvl2"] = round(total_returns - INITIAL_CAPITAL, 2)
            performance_list.append(hour_row)
        df = pd.DataFrame(performance_list)
        till_date_df = pd.read_csv(
            f"data/algorithm_input-{symbol}-{till_date}-{strategy_type}.csv"
        )
        till_date_df = pd.merge(
            till_date_df, df[["hour", "performance_lvl2"]], on="hour"
        )
        till_date_df["trade_lvl2"] = till_date_df.apply(
            lambda row: (row.trade_lvl1 and row.performance_lvl2 > 0),
            axis=1,
        )
        print(f"level 2 algorithm input for {symbol} on {till_date} ({strategy_type}):")
        print(till_date_df)
        till_date_df.to_csv(
            f"data/algorithm_input-{symbol}-{till_date}-{strategy_type}-lvl2.csv",
            index=False,
        )
        if USE_DISCORD:
            post_to_discord(
                DiscordMessage(
                    channel_id=DISCORD_CHANNEL_WAITING_ID,
                    messages=[
                        f"Level 2 algorithm input for {symbol} on {till_date} ({strategy_type}).",
                        f"Save as algorithm_input/algorithm_input-{symbol}-{till_date}-{strategy_type}-lvl2.csv",
                        f"""```
{till_date_df.to_csv(index=False)}
```""",
                    ],
                )
            )
