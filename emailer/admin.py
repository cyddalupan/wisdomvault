from django.urls import path, reverse
from django import forms
from django.contrib import admin
from django.shortcuts import render
from django.core.mail import send_mass_mail
from django.conf import settings
from django.http import HttpResponseRedirect
from .models import EmailList, EmailSent

class EmailBlastForm(forms.Form):
    emails = forms.ModelMultipleChoiceField(
        queryset=EmailList.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Emails', is_stacked=False)
    )
    subject = forms.CharField(max_length=255)
    body = forms.CharField(widget=forms.Textarea)

def email_blast_view(request, admin_site):
    form = EmailBlastForm()
    if request.method == 'POST':
        form = EmailBlastForm(request.POST)
        if form.is_valid():
            selected_emails = form.cleaned_data['emails']
            subject = form.cleaned_data['subject']
            body = form.cleaned_data['body']
            email_tuples = [
                (subject, body, settings.EMAIL_HOST_USER, [email_obj.email]) for email_obj in selected_emails
            ]

            send_mass_mail(email_tuples, fail_silently=False)

            for email_obj in selected_emails:
                EmailSent.objects.create(email=email_obj.email, subject=subject, body=body, status='sent')

            admin_site.message_user(request, "Emails have been sent successfully.")
            return HttpResponseRedirect("../")

    return render(request, 'admin/email_blast.html', {'form': form, 'opts': admin_site.app_index})

class EmailListAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'created_at')
    search_fields = ('email', 'name')
    change_list_template = "admin/email_list_change_list.html"

    def get_urls(self):
        # Additional URL patterns for the admin class
        urls = super().get_urls()
        my_urls = [
            path('send-email-blast/', self.admin_site.admin_view(self.send_email_blast_view), name='send-email-blast'),
        ]
        return my_urls + urls
    
    def send_email_blast_view(self, request):
        form = EmailBlastForm()
        if request.method == 'POST':
            form = EmailBlastForm(request.POST)
            if form.is_valid():
                selected_emails = form.cleaned_data['emails']
                subject = form.cleaned_data['subject']
                body = form.cleaned_data['body']
                email_tuples = [
                    (subject, body, settings.EMAIL_HOST_USER, [email_obj.email]) for email_obj in selected_emails
                ]

                send_mass_mail(email_tuples, fail_silently=False)

                for email_obj in selected_emails:
                    EmailSent.objects.create(email=email_obj.email, subject=subject, body=body, status='sent')

                self.message_user(request, "Emails have been sent successfully.")
                return HttpResponseRedirect("../")

        return render(request, 'admin/email_blast.html', {'form': form, 'opts': self.model._meta})

admin.site.register(EmailList, EmailListAdmin)