from rest_framework.routers import DefaultRouter
from django.urls import include, path

from project.apps.core.viewsets import UserViewset, PositionViewset


router = DefaultRouter()
router.register("users", UserViewset, basename="user")
router.register("positions", PositionViewset, basename="position")

urlpatterns = [
    path("", include(router.urls)),
]
