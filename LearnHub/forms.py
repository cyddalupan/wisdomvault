from django import forms
from .models import DigitalMarketing

class DigitalMarketingForm(forms.ModelForm):
    class Meta:
        model = DigitalMarketing
        fields = ['user_input']