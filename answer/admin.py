from django.contrib import admin
from .models import QuestionAnswer
from dotenv import load_dotenv
from openai import OpenAI
from django.utils.text import Truncator
from django.contrib.auth.models import User
from django.db import models

load_dotenv()

client = OpenAI()

class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ('title', 'short_question', 'short_answer')
    fields = ('title', 'question', 'formatted_answer')
    readonly_fields = ('formatted_answer', 'answer')

    def short_question(self, obj):
        return Truncator(obj.question).chars(50)
    short_question.short_description = 'Question'

    def short_answer(self, obj):
        return Truncator(obj.answer).chars(50)
    short_answer.short_description = 'Answer'

    def save_model(self, request, obj, form, change):
        messages = [
            {"role": "system", "content": 'Utilize Markdown format. Give Direct Answer'},
        ]
        messages.append({"role": "user", "content": obj.question})
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        response_content = completion.choices[0].message.content
        obj.answer = response_content

        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Filter only QuestionAnswer objects created by current user
        return qs.filter(created_by=request.user)

# Register the model and the admin class
admin.site.register(QuestionAnswer, QuestionAnswerAdmin)
