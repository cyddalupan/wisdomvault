from django import forms
from .models import DigitalMarketing

class LearnHubForm(forms.ModelForm):
    class Meta:
        model = DigitalMarketing
        fields = ['user_input']
        widgets = {
            'user_input': forms.Textarea(attrs={
                'class': 'form-control',  # Bootstrap styling
                'rows': 3,               # Adjust the height of the textarea
                'placeholder': 'Enter your input here...',  # Optional placeholder
            }),
        }
