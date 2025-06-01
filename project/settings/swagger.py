from .settings import INSTALLED_APPS


INSTALLED_APPS += ["drf_spectacular"]

SPECTACULAR_SETTINGS = {
    "TITLE": "Auto Journaling",
    "DESCRIPTION": "Swagger API interface for Auto Journaling Backend",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
