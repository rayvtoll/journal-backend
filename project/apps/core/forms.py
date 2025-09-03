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
    sl = forms.FloatField(label="Stop Loss (%)", initial=0.475)
    tp = forms.FloatField(label="Take Profit (%)", initial=5)
    start_date_gte = forms.DateField(label="Start Date (gte)", required=False)
    start_date_lt = forms.DateField(label="Start Date (lt)", required=False)
    use_tp1 = forms.BooleanField(label="Use TP 1", required=False)
    tp1 = forms.FloatField(label="TP 1 (%)", initial=50)
    tp1_amount = forms.FloatField(label="TP 1 Amount", initial=20)
    use_tp2 = forms.BooleanField(label="Use TP 2", required=False)
    tp2 = forms.FloatField(label="TP 2 (%)", initial=70)
    tp2_amount = forms.FloatField(label="TP 2 Amount", initial=50)
    hours = forms.MultipleChoiceField(
        label="Hours",
        choices=[(i, i) for i in range(1, 25)],
        widget=forms.CheckboxSelectMultiple,
        initial=[2, 3, 4, 15, 17, 18],
    )
    week_days = forms.MultipleChoiceField(
        label="Week Days",
        choices=FORM_DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    min_liquidation_amount = forms.IntegerField(
        label="Min Liquidation Amount", required=False
    )
    max_liquidation_amount = forms.IntegerField(
        label="Max Liquidation Amount", required=False
    )
