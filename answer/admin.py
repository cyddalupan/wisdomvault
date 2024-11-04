from django.contrib import admin
from .models import QuestionAnswer

class QuestionAnswerAdmin(admin.ModelAdmin):
    # Define the fields to display in the admin
    list_display = ('title', 'question', 'answer')

    # Specify the fields to be displayed in the form
    fields = ('title', 'question', 'answer')

    # Make the 'answer' field read-only
    readonly_fields = ('answer',)

# Register the model and the custom admin class
admin.site.register(QuestionAnswer, QuestionAnswerAdmin)