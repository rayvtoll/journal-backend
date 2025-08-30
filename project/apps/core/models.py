from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.db import models


class User(AbstractUser):
    """User model"""

    pass


class Position(models.Model):
    """Position model"""

    class _PostionSideChoices(models.TextChoices):
        LONG = "LONG", "LONG"
        SHORT = "SHORT", "SHORT"

    class _TimeFrameChoices(models.TextChoices):
        ONE_MINUTE = "1m", "1 Minute"
        FIVE_MINUTES = "5m", "5 Minutes"
        FIFTEEN_MINUTES = "15m", "15 Minutes"

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
    time_frame = models.CharField(
        max_length=5,
        choices=_TimeFrameChoices.choices,
        default=_TimeFrameChoices.FIVE_MINUTES,
    )

    start = models.DateTimeField()
    entry_price = models.FloatField(null=True, blank=True)
    entry_fee = models.FloatField(null=True, blank=True)

    end = models.DateTimeField(null=True, blank=True)
    closing_price = models.FloatField(null=True, blank=True)
    closing_fee = models.FloatField(null=True, blank=True)

    @property
    def admin_url(self):
        content_type = ContentType.objects.get_for_model(self.__class__)
        return reverse(
            "admin:%s_%s_change" % (content_type.app_label, content_type.model),
            args=(self.id,),
        )

    @property
    def returns(self) -> float:
        """Calculate the returns for the position."""

        return_value = 0.00
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

class OHLCV(models.Model):
    """OHLCV model for storing Open, High, Low, Close, Volume data."""

    symbol = models.CharField(max_length=20)
    timeframe = models.CharField(max_length=5, default="5m")
    datetime = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()

    class Meta:
        unique_together = ("symbol", "timeframe", "datetime")

    def __str__(self):
        """String representation of the OHLCV model."""
        return f"OHLCV[{self.symbol} - {self.timeframe} - {self.datetime}]"
