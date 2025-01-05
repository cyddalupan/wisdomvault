import logging
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from .models import DigitalMarketing
from .forms import DigitalMarketingForm
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

class DigitalMarketingAdmin(admin.ModelAdmin):
    change_list_template = "admin/learnhub.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('digital-marketing/', self.admin_site.admin_view(self.digital_marketing), name='digital_marketing'),
        ]
        return custom_urls + urls

    def digital_marketing(self, request):
        form = DigitalMarketingForm(request.POST or None)
        ai_response = ''
        latest_digital_marketing = None

        if request.method == 'POST' and form.is_valid():
            digital_marketing_instance = form.save(commit=False)
        
            digital_marketing_instance.ai_response = self.perform_digital_marketing(
                digital_marketing_instance.user_input
            )
            digital_marketing_instance.save()
            ai_response = digital_marketing_instance.formatted_output
        else:
            if DigitalMarketing.objects.exists():
                latest_digital_marketing = DigitalMarketing.objects.latest('id')

        context = dict(
            self.admin_site.each_context(request),
            form=form,
            ai_response=ai_response,
            latest_digital_marketing=latest_digital_marketing,
        )
        return render(request, "admin/learnhub.html", context)

    def changelist_view(self, request, extra_context=None):
        return self.digital_marketing(request)

    def perform_digital_marketing(self, text):
        messages = [
            {"role": "system", "content": 'you are a digital marketing teacher.'},
            {"role": "user", "content": text},
        ]
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise e

# Register the model and admin class
admin.site.register(DigitalMarketing, DigitalMarketingAdmin)
