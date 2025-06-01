from rest_framework import serializers

from project.apps.core.models import Position, User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""

    class Meta:
        model = User
        fields = "__all__"


class PositionSerializer(serializers.ModelSerializer):
    """Serializer for the Position model."""

    returns = serializers.SerializerMethodField("get_returns")

    def get_returns(self, obj) -> float:
        """Calculate the returns for the position."""

        return obj.returns

    class Meta:
        model = Position
        fields = "__all__"
