from typing import List
import matplotlib.pyplot as plt
import seaborn as sns

from django.db.models import QuerySet
from django.utils import timezone
from django.views.generic.edit import FormView

from project.apps.core.filters import PositionFilterSet
from project.apps.core.forms import WhatIfPerHourForm
from project.apps.core.models import Position, OHLCV
from project.apps.core.tables import WhatIfPerHourPositionTable

from .helpers import COLOR_LIST, SNS_THEME


class PositionWhatIfPerHourView(FormView):
    """List view for positions with table and filter functionality."""

    template_name = "core/what_if_per_hour.html"
    model = Position
    table_class = WhatIfPerHourPositionTable
    filterset_class = PositionFilterSet
    form_class = WhatIfPerHourForm

    def form_valid(self, form: WhatIfPerHourForm):
        plt.rcParams["axes.prop_cycle"] = plt.cycler(color=COLOR_LIST)
        sns.set_theme(**SNS_THEME)
        sns.set_context(
            "notebook",
            rc={
                "font.size": 6,
                "axes.titlesize": 12,
                "axes.labelsize": 10,
            },
        )

        use_reverse: bool = True
        hours: List[int] = form.cleaned_data["hours"]

        table_rows: List[dict] = []
        for hour in range(24) if not hours else hours:
            table_row = {"hour": hour}
            for name, reversed in {
                "live": False,
                "reversed": True,
                "grey": False,
            }.items():
                positions: QuerySet[Position] = self.model.objects.filter(
                    candles_before_entry=1,
                    start__hour=hour,
                )
                if start_date_gte := form.cleaned_data["start_date_gte"]:
                    positions = positions.filter(start__gte=start_date_gte)
                if start_date_lt := form.cleaned_data["start_date_lt"]:
                    positions = positions.filter(start__lt=start_date_lt)
                if weekdays := form.cleaned_data["week_days"]:
                    positions = positions.filter(start__week_day__in=weekdays)

                positions = positions.order_by("start")

                wins = 0
                losses = 0
                tp: float = form.cleaned_data[f"{name}_tp"]
                sl: float = form.cleaned_data[f"{name}_sl"]
                for position in positions:
                    position.what_if_returns = 0
                    if use_reverse:
                        if reversed and position.strategy_type != "reversed":
                            position.side = (
                                "SHORT" if position.side == "LONG" else "LONG"
                            )

                        elif not reversed and position.strategy_type == "reversed":
                            position.side = (
                                "SHORT" if position.side == "LONG" else "LONG"
                            )

                    ohlcv_s = OHLCV.objects.filter(
                        datetime__gte=position.start,
                        datetime__lt=position.start + timezone.timedelta(days=28),
                    ).order_by("datetime")
                    if ohlcv_s.exists():
                        entry_price = ohlcv_s.first().open
                    for candle in ohlcv_s:
                        if position.side == "LONG":

                            # SL
                            if candle.low <= entry_price - (entry_price * sl / 100):
                                losses += 1
                                break

                            # TP
                            if candle.close >= entry_price + (entry_price * tp / 100):
                                wins += 1
                                break

                        if position.side == "SHORT":

                            # SL
                            if candle.high >= entry_price + (entry_price * sl / 100):
                                losses += 1
                                break

                            # TP
                            if candle.close <= entry_price - (entry_price * tp / 100):
                                wins += 1
                                break

                table_row[f"{name}_nr_of_trades"] = wins + losses
                table_row[f"{name}_ratio"] = round(
                    (wins / (wins + losses)) if wins and losses else 0, 2
                )
                table_row[f"{name}_nr_of_r_s"] = round(
                    (tp / sl * wins) - (losses * 1.2), 2
                )
            print(table_row)
            table_rows.append(table_row)

        return self.render_to_response(
            self.get_context_data(
                form=form,
                table=self.table_class(table_rows),
                title="What if per hour analysis",
            )
        )
