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
    use_rsi = forms.BooleanField(label="Use RSI Filter", required=False)
    use_reverse = forms.BooleanField(
        label="Use Reverse Strategy", required=False, initial=True
    )
    reverse_all = forms.BooleanField(label="Reverse LONG-SHORT", required=False)
    compound = forms.BooleanField(label="Compound", initial=True, required=False)
    no_overlap = forms.BooleanField(label="No Overlap", required=False)
    strategy_types = forms.MultipleChoiceField(
        label="Strategy Types",
        choices=[
            ("live", "Live"),
            ("reversed", "Reversed"),
            ("journaling", "Journaling"),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    sl = forms.FloatField(label="Stop Loss (%)", initial=0.5)
    tp = forms.FloatField(label="Take Profit (%)", initial=5)
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
    hours = forms.MultipleChoiceField(
        label="Hours",
        choices=[(i, i) for i in range(0, 24)],
        widget=forms.CheckboxSelectMultiple,
        initial=[2, 3, 4],
    )
    week_days = forms.MultipleChoiceField(
        label="Week Days",
        choices=FORM_DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        initial=[2, 3, 4, 5, 6, 7, 1]
    )
    min_liquidation_amount = forms.IntegerField(
        label="Min Liquidation Amount", required=False
    )
    max_liquidation_amount = forms.IntegerField(
        label="Max Liquidation Amount", required=False
    )
    percentage_per_trade = forms.FloatField(
        label="Percentage per Trade (%)", initial=1, required=False
    )


class WhatIfPerHourForm(forms.Form):
    live_sl = forms.FloatField(label="Live SL (%)", initial=0.5)
    live_tp = forms.FloatField(label="Live TP (%)", initial=5.0)
    grey_sl = forms.FloatField(label="Grey SL (%)", initial=0.8)
    grey_tp = forms.FloatField(label="Grey TP (%)", initial=4.0)
    reversed_sl = forms.FloatField(label="Reversed SL (%)", initial=0.4)
    reversed_tp = forms.FloatField(label="Reversed TP (%)", initial=4.0)
    start_date_gte = forms.DateField(label="Start Date (gte)", required=False)
    start_date_lt = forms.DateField(label="Start Date (lt)", required=False)
    week_days = forms.MultipleChoiceField(
        label="Week Days",
        choices=FORM_DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        initial=[2, 3, 4, 5, 6, 7, 1]
    )
    hours = forms.MultipleChoiceField(
        label="Hours",
        choices=[(i, i) for i in range(0, 24)],
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
