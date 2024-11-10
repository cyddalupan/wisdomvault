from django.urls import path, reverse
from django import forms
from django.contrib import admin
from django.shortcuts import render
from django.core.mail import send_mass_mail
from django.conf import settings
from django.http import HttpResponseRedirect
from .models import Category, EmailList, EmailSent
from django.core.mail import EmailMultiAlternatives

class EmailBlastForm(forms.Form):
    emails = forms.ModelMultipleChoiceField(
        queryset=EmailList.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Emails', is_stacked=False)
    )
    subject = forms.CharField(max_length=255)
    body = forms.CharField(widget=forms.Textarea)

class EmailListAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'category', 'created_at')
    search_fields = ('email', 'name',  'category')
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
                sender_name = 'WisdomVault'
                sender_email = settings.EMAIL_HOST_USER
                sender = f"{sender_name} <{sender_email}>"

                for email_obj in selected_emails:
                    email_message = EmailMultiAlternatives(
                        subject=subject,
                        body=body,
                        from_email=sender,
                        to=[email_obj.email]
                    )
                    email_message.send()
                    
                    EmailSent.objects.create(email=email_obj.email, subject=subject, body=body, status='sent')

                self.message_user(request, "Emails have been sent successfully.")
                return HttpResponseRedirect("../")

        return render(request, 'admin/email_blast.html', {'form': form, 'opts': self.model._meta})

admin.site.register(EmailList, EmailListAdmin)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)