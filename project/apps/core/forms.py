from django import forms


class WhatIfForm(forms.Form):
    sl = forms.FloatField(label="Stop Loss (%)", initial=0.5)
    tp = forms.FloatField(label="Take Profit (%)", initial=5)
    start_date_gte = forms.DateField(label="Start Date (gte)", required=False)
    use_tp1 = forms.BooleanField(label="Use TP 1", initial=True, required=False)
    tp1 = forms.FloatField(label="TP 1 (%)", initial=50)
    tp1_amount = forms.FloatField(label="TP 1 Amount", initial=20)
    use_tp2 = forms.BooleanField(label="Use TP 2", initial=True, required=False)
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
        choices=[(i, f"{i+1}") for i in range(0, 7)],
        widget=forms.CheckboxSelectMultiple,
        initial=[0, 1, 2, 3, 4, 5, 6],
    )
    min_liquidation_amount = forms.IntegerField(
        label="Min Liquidation Amount", required=False
    )
    max_liquidation_amount = forms.IntegerField(
        label="Max Liquidation Amount", required=False
    )
