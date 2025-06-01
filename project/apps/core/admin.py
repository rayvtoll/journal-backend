from import_export.admin import ImportExportModelAdmin
from django.contrib import admin

from .models import User, Position


@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    model = User


@admin.register(Position)
class PositionAdmin(ImportExportModelAdmin):
    model = Position
