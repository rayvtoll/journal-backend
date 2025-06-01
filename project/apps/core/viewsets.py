from typing import List
import django_filters
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework.viewsets import ModelViewSet

from project.apps.core.models import Position, User
from project.apps.core.serializers import PositionSerializer, UserSerializer


def swagger_class_decorator(tag, actions=None) -> extend_schema_view:
    """Returns the extend_schema_view decorator with the given tag and actions."""

    if not actions:
        actions = [
            "list",
            "retrieve",
            "create",
            "update",
            "partial_update",
            "destroy",
        ]
    return extend_schema_view(
        **{action: extend_schema(tags=[tag]) for action in actions}
    )


class BaseViewSet:
    """Base viewset that provides common functionality for all viewsets."""

    ordering_fields = "__all__"
    page_size_query_param = "page_size"
    filterset_fields = "__all__"

    @property
    def filterset_fields(self) -> List[str]:
        return [field.name for field in self.model._meta.fields]

    def get_queryset(self):
        """Returns the queryset for the viewset."""
        return self.model.objects.all().order_by("-id")


@swagger_class_decorator("Users")
class UserViewset(BaseViewSet, ModelViewSet):
    """Viewset for the User model."""

    model = User
    serializer_class = UserSerializer


class PositionFilterSet(django_filters.FilterSet):
    """FilterSet for the Position model."""

    week_day = django_filters.CharFilter(
        field_name="start__week_day", lookup_expr="exact"
    )
    hour = django_filters.CharFilter(field_name="start__hour", lookup_expr="exact")
    week_days = django_filters.NumericRangeFilter(
        field_name="start__week_day", lookup_expr="range"
    )
    hours = django_filters.NumericRangeFilter(
        field_name="start__hour", lookup_expr="range"
    )

    class Meta:
        model = Position
        fields = "__all__"


@swagger_class_decorator("Positions")
class PositionViewset(BaseViewSet, ModelViewSet):
    """Viewset for the Position model."""

    model = Position
    serializer_class = PositionSerializer
    filterset_class = PositionFilterSet

    @property
    def filterset_fields(self) -> List[str]:
        return super().filterset_fields + ["start__week_day"]

    def list(self, request, *args, **kwargs):
        """List all positions."""
        return_list = super().list(request, *args, **kwargs)
        returns = sum(
            [position.returns for position in self.filter_queryset(self.get_queryset())]
        )
        return_list.data["returns"] = returns
        return return_list
