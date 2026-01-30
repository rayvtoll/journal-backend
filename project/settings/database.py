from decouple import config

from .settings import BASE_DIR

DB_ENGINE = config("DB_ENGINE", "django.db.backends.sqlite3")
DB_NAME = config("DB_NAME", "db.sqlite3")


def create_database_settings():
    DB_SETTINGS = {
        "ENGINE": DB_ENGINE,
    }

    if DB_NAME == "db.sqlite3":
        DB_SETTINGS["NAME"] = BASE_DIR / DB_NAME
    else:
        DB_SETTINGS["NAME"] = config("DB_NAME")
        DB_SETTINGS["USER"] = config("DB_USER")
        DB_SETTINGS["PASSWORD"] = config("DB_PASSWORD")
        DB_SETTINGS["HOST"] = config("DB_HOST")
        DB_SETTINGS["PORT"] = config("DB_PORT")

    return DB_SETTINGS


DATABASES = {"default": create_database_settings()}
