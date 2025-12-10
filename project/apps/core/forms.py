from django import forms

FORM_DAY_CHOICES = [
    (2, "Monday"),
    (3, "Tuesday"),
    (4, "Wednesday"),
    (5, "Thursday"),
    (6, "Friday"),
    (7, "Saturday"),
    (1, "Sunday"),
]


class WhatIfForm(forms.Form):
    live_candles_before_entry = forms.MultipleChoiceField(
        label="Candles Before Entry",
        choices=[(i, i) for i in range(1, 12)],
        widget=forms.CheckboxSelectMultiple,
        initial=[1],
    )
    reversed_candles_before_entry = forms.MultipleChoiceField(
        label="Reversed Candles Before Entry",
        choices=[(i, i) for i in range(1, 12)],
        widget=forms.CheckboxSelectMultiple,
        initial=[1, 2],
    )
    use_rsi = forms.BooleanField(label="Use RSI Filter", required=False)
    rsi_lower = forms.IntegerField(label="RSI Lower", initial=30)
    rsi_upper = forms.IntegerField(label="RSI Upper", initial=70)
    rsi_sell_percentage = forms.FloatField(
        label="RSI Sell Percentage (%)", initial=10.0
    )
    compound = forms.BooleanField(label="Compound", initial=True, required=False)
    no_overlap = forms.BooleanField(label="No Overlap", required=False)
    strategy_types = forms.MultipleChoiceField(
        label="Strategy Types",
        choices=[
            ("live", "Live"),
            ("reversed", "Reversed"),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    live_sl = forms.FloatField(label="Live Stop Loss (%)", initial=1)
    live_tp = forms.FloatField(label="Live Take Profit (%)", initial=4)
    reversed_sl = forms.FloatField(label="Reversed Stop Loss (%)", initial=1)
    reversed_tp = forms.FloatField(label="Reversed Take Profit (%)", initial=4)
    start_date_gte = forms.DateField(label="Start Date (gte)", required=False)
    start_date_lt = forms.DateField(label="Start Date (lt)", required=False)
    use_trailing_sl = forms.BooleanField(label="Use Trailing SL", required=False)
    trailing_sl = forms.FloatField(label="Trailing SL (%)", initial=1)
    use_sl_to_entry = forms.BooleanField(label="Use SL to Entry", required=False)
    sl_to_entry = forms.FloatField(label="SL to Entry (%)", initial=50)
    use_tp1 = forms.BooleanField(label="Use TP 1", required=False)
    tp1 = forms.FloatField(label="TP 1 (%)", initial=50)
    tp1_amount = forms.FloatField(label="TP 1 Amount", initial=20)
    use_tp2 = forms.BooleanField(label="Use TP 2", required=False)
    tp2 = forms.FloatField(label="TP 2 (%)", initial=70)
    tp2_amount = forms.FloatField(label="TP 2 Amount", initial=50)
    use_tp3 = forms.BooleanField(label="Use TP 3", required=False)
    tp3 = forms.FloatField(label="TP 3 (%)", initial=85)
    tp3_amount = forms.FloatField(label="TP 3 Amount", initial=20)
    use_tp4 = forms.BooleanField(label="Use TP 4", required=False)
    tp4 = forms.FloatField(label="TP 4 (%)", initial=95)
    tp4_amount = forms.FloatField(label="TP 4 Amount", initial=5)
    use_tp5 = forms.BooleanField(label="Use TP 5", required=False)
    tp5 = forms.FloatField(label="TP 5 (%)", initial=99)
    tp5_amount = forms.FloatField(label="TP 5 Amount", initial=5)
    use_tp6 = forms.BooleanField(label="Use TP 6", required=False)
    tp6 = forms.FloatField(label="TP 6 (%)", initial=100)
    tp6_amount = forms.FloatField(label="TP 6 Amount", initial=5)
    use_tp7 = forms.BooleanField(label="Use TP 7", required=False)
    tp7 = forms.FloatField(label="TP 7 (%)", initial=100)
    tp7_amount = forms.FloatField(label="TP 7 Amount", initial=5)
    use_tp8 = forms.BooleanField(label="Use TP 8", required=False)
    tp8 = forms.FloatField(label="TP 8 (%)", initial=100)
    tp8_amount = forms.FloatField(label="TP 8 Amount", initial=5)
    use_tp9 = forms.BooleanField(label="Use TP 9", required=False)
    tp9 = forms.FloatField(label="TP 9 (%)", initial=100)
    tp9_amount = forms.FloatField(label="TP 9 Amount", initial=5)
    hours = forms.MultipleChoiceField(
        label="Hours",
        choices=[(i, i) for i in range(0, 24)],
        widget=forms.CheckboxSelectMultiple,
        initial=[2, 3, 4, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
    )
    week_days = forms.MultipleChoiceField(
        label="Week Days",
        choices=FORM_DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        initial=[2, 3, 4, 5, 6, 7, 1],
    )
    min_liquidation_amount = forms.IntegerField(
        label="Min Liquidation Amount", required=False, initial=2000
    )
    max_liquidation_amount = forms.IntegerField(
        label="Max Liquidation Amount", required=False
    )
    percentage_per_trade = forms.FloatField(
        label="Percentage per Trade (%)", initial=1, required=False
    )


FORM_DAY_TOGETHER_CHOICES = [
    (0, "Monday"),
    (1, "Tuesday"),
    (2, "Wednesday"),
    (3, "Thursday"),
    (4, "Friday"),
    (5, "Saturday"),
    (6, "Sunday"),
]


class WhatIfPerHourForm(forms.Form):
    sl = forms.FloatField(label="SL (%)", initial=1)
    tp = forms.FloatField(label="TP (%)", initial=4.0)
    start_date_gte = forms.DateField(label="Start Date (gte)", required=False)
    start_date_lt = forms.DateField(label="Start Date (lt)", required=False)
    week_days = forms.MultipleChoiceField(
        label="Week Days",
        choices=FORM_DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        initial=[2, 3, 4, 5, 6, 7, 1],
    )
    hours = forms.MultipleChoiceField(
        label="Hours",
        choices=[(i, i) for i in range(0, 24)],
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
