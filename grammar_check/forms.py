from django import forms
from .models import GrammarCheck

class GrammarCheckForm(forms.ModelForm):
    class Meta:
        model = GrammarCheck
        fields = ['user_input']