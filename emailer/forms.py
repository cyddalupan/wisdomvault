from django import forms

class EmailForm(forms.Form):
    recipient = forms.EmailField(label='Recipient Email')
    subject = forms.CharField(max_length=255)
    message = forms.CharField(widget=forms.Textarea)