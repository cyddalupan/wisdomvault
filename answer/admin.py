from django.contrib import admin
from .models import QuestionAnswer
from dotenv import load_dotenv
from openai import OpenAI
from django.utils.text import Truncator
load_dotenv()

client = OpenAI()

class QuestionAnswerAdmin(admin.ModelAdmin):
    # Define the fields to display in the admin
    list_display = ('title', 'short_question', 'short_answer')

    # Specify the fields to be displayed in the form
    fields = ('title', 'question', 'formatted_answer')

    # Make the 'answer' field read-only
    readonly_fields = ('formatted_answer', 'answer')

    # Function to truncate and display short version of question
    def short_question(self, obj):
        return Truncator(obj.question).chars(50)
    short_question.short_description = 'Question'

    # Function to truncate and display short version of answer
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
        super().save_model(request, obj, form, change)

# Register the model and the custom admin class
admin.site.register(QuestionAnswer, QuestionAnswerAdmin)