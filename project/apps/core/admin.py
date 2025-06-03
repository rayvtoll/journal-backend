from import_export.admin import ImportExportModelAdmin
from django.contrib import admin

from .models import User, Position


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
