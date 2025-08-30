from import_export.admin import ImportExportModelAdmin
from django.contrib import admin

from .models import User, Position, OHLCV


@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    model = User


@admin.register(Position)
class PositionAdmin(ImportExportModelAdmin):
    model = Position
    list_display = (
        "id",
        "start",
        "end",
        "side",
        "returns",
        "entry_price",
        "closing_price",
    )
    list_filter = ("side", "amount", "start", "end")


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
