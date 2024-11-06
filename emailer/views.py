from django.http import BadHeaderError
from django.shortcuts import render

# Create your views here.
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from .forms import EmailForm
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_email(request):
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            try: 
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,  # From email
                    [recipient],              # To email
                    fail_silently=False,
                )
            except BadHeaderError:
                logger.error("Invalid header found.")
            except Exception as e:
                logger.error(f"Failed to send email: {e}")

            #return redirect('success')  # Assume you have a success page
    else:
        form = EmailForm()

    return render(request, 'emailer/send_email.html', {'form': form})