from import_export.admin import ImportExportModelAdmin
from django.contrib import admin

from project.apps.core.models import User, Position, OHLCV, Liquidation


@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    model = User


@admin.register(Position)
class PositionAdmin(ImportExportModelAdmin):
    model = Position
    list_display = (
        "id",
        "strategy_type",
        "candles_before_entry",
        "liquidation_datetime",
        "start",
        "side",
        "entry_price",
    )
    list_filter = ("side", "strategy_type", "liquidation_datetime")


@admin.register(OHLCV)
class OHLCVAdmin(ImportExportModelAdmin):
    model = OHLCV
    list_display = (
        "id",
        "symbol",
        "timeframe",
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )
    list_filter = ("symbol", "timeframe", "datetime")


@admin.register(Liquidation)
class LiquidationAdmin(ImportExportModelAdmin):
    model = Liquidation
    list_display = (
        "id",
        "timeframe",
        "symbol",
        "datetime",
        "side",
        "amount",
    )
    list_filter = ("symbol", "timeframe", "side", "datetime")
