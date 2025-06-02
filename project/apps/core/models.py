from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """User model"""

    pass


class Position(models.Model):
    """Position model"""

    class _PostionSideChoices(models.TextChoices):
        LONG = "LONG", "LONG"
        SHORT = "SHORT", "SHORT"

    side = models.CharField(
        max_length=10,
        choices=_PostionSideChoices.choices,
        default=_PostionSideChoices.LONG,
    )
    take_profit_price = models.FloatField(null=True, blank=True)
    stop_loss_price = models.FloatField(null=True, blank=True)
    amount = models.FloatField()
    candles_before_entry = models.IntegerField(null=True, blank=True)
    liquidation_amount = models.IntegerField(null=True, blank=True)
    nr_of_liquidations = models.IntegerField(null=True, blank=True)

    start = models.DateTimeField()
    entry_price = models.FloatField(null=True, blank=True)
    entry_fee = models.FloatField(null=True, blank=True)

    end = models.DateTimeField(null=True, blank=True)
    closing_price = models.FloatField(null=True, blank=True)
    closing_fee = models.FloatField(null=True, blank=True)

    @property
    def returns(self) -> float:
        """Calculate the returns for the position."""

        return_value = 0.0
        return_value -= self.entry_fee if self.entry_fee else 0
        return_value -= self.closing_fee if self.closing_fee else 0
        if self.entry_price and self.closing_price and self.amount:
            match self.side:
                case self._PostionSideChoices.LONG:
                    return_value += (
                        self.closing_price - self.entry_price
                    ) * self.amount
                case self._PostionSideChoices.SHORT:
                    return_value += (
                        self.entry_price - self.closing_price
                    ) * self.amount
        return round(return_value, 2)

    def __str__(self):
        """String representation of the Position model."""
        return f"Position[{self.id}]"
