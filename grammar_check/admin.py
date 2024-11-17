from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from .models import GrammarCheck
from .forms import GrammarCheckForm
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

class GrammarCheckAdmin(admin.ModelAdmin):
    change_list_template = "admin/grammar_check.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('grammar-check/', self.admin_site.admin_view(self.grammar_check), name='grammar_check'),
        ]
        return custom_urls + urls

    def grammar_check(self, request):
        form = GrammarCheckForm(request.POST or None)
        corrected_text = ''
        latest_grammar_check = None
        
        if request.method == 'POST' and form.is_valid():
            grammar_check_instance = form.save(commit=False)
            grammar_check_instance.corrected_output = self.perform_grammar_check(grammar_check_instance.user_input)
            grammar_check_instance.save()
            corrected_text = grammar_check_instance.formatted_output
            latest_grammar_check = grammar_check_instance
            
        else:
            # Handle the case where no GrammarCheck objects exist
            if GrammarCheck.objects.exists():
                latest_grammar_check = GrammarCheck.objects.latest('id')

        context = dict(
            self.admin_site.each_context(request),
            form=form,
            corrected_text=corrected_text,
            latest_grammar_check=latest_grammar_check,
        )
        return render(request, "admin/grammar_check.html", context)

    def changelist_view(self, request, extra_context=None):
        # Redirect to our custom view
        response = self.grammar_check(request)
        return response

    def perform_grammar_check(self, text):
        messages = [
            {"role": "system", "content": 'User will send message and you will improve that message. make is respectful and easy to understand.'},
        ]
        messages.append({"role": "user", "content": text})
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return completion.choices[0].message.content

# Register the model and admin class
admin.site.register(GrammarCheck, GrammarCheckAdmin)