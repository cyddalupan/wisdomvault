import json
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
        message = ""
        topic_score = 0

        if request.method == 'POST' and form.is_valid():
            digital_marketing_instance = form.save(commit=False)
            user_profile = request.user

            # TODO: Update getting course
            course = Course.objects.first()

            # Call the AI function with user input and course details
            response_json = self.perform_digital_marketing(
                digital_marketing_instance.user_input, user_profile, course
            )

            print("JSON TESTER", response_json)
            
            if not response_json:
                response_json = '{"message": "No response received.", "topic_score": 0}'

            # Parse the JSON response string
            response_data = json.loads(response_json)

            # Extract json
            message = response_data.get('message', '')
            topic_score = response_data.get('topic_score', 0)
            print("message", message)
            print("topic_score", topic_score)

            # Store the message
            digital_marketing_instance.ai_response = message

            # Save the instance
            digital_marketing_instance.save()

            # Use formatted output for rendering
            ai_response = digital_marketing_instance.formatted_output
        else:
            # Load the latest digital marketing instance for display if it exists
            if DigitalMarketing.objects.exists():
                latest_digital_marketing = DigitalMarketing.objects.latest('id')

        # Pass context to the template
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            ai_response=ai_response,
            topic_score=topic_score,
            latest_digital_marketing=latest_digital_marketing,
        )
        return render(request, "admin/learnhub.html", context)

    def changelist_view(self, request, extra_context=None):
        return self.digital_marketing(request)

    def perform_digital_marketing(self, text, user_profile, course):
        user_progress = LessonProgress.objects.filter(user=user_profile, course=course).first()
        if not user_progress:
            first_lesson = course.lessons.order_by('order').first()
            user_progress = LessonProgress.objects.create(
                user=user_profile,
                course=course,
                lesson=first_lesson,
                completed=False
            )
        lesson = user_progress.lesson
        latest_chat = ChatHistory.objects.create(
            user=user_profile, 
            lesson=lesson,
            message=text,
            reply='')
        chat_history = ChatHistory.objects.filter(user=user_profile, lesson=lesson).order_by('-timestamp')[:20]
        chat_history = list(chat_history)[::-1]

        print("HISTORY", chat_history)

        messages = [
            {
                "role": "system", 
                "content": (
                    "You are an API that always returns a JSON object. "
                    "The format must strictly adhere to: "
                    '{"message": "string (can include markdown)", "topic_score": integer (1-100)}. '
                    f"You are a teacher instructing the user about {course}, focusing on the topic: {lesson.name}. "
                    "Use taglish but depends on the user"
                    "You quizzes every 3 conversation to assess the user's understanding."
                    "Your scoring for topic_score must be strict and ensure there is no cheating."
                    "topic_score sould starts at 1 and move up as the user improves"
                    f"before you give 100 points on topic_score you make sure that the user is expert on the topic: {lesson.name}"
                    "Output only the JSON object without any additional text."
                )
            },
        ]

        print("raw message", messages)
        
        # Include previous chat history in the conversation
        for chat in chat_history:
            messages.append({"role": "user", "content": chat.message})
            if chat.reply and chat.reply != "":
                messages.append({"role": "system", "content": chat.reply})

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            ai_reply = completion.choices[0].message.content
            print("raw ai_reply", ai_reply)

            latest_chat.reply = ai_reply
            latest_chat.save()
            return ai_reply
        except Exception as e:
            print(f"Error in AI response: {e}")
            # Return a fallback JSON if there's an error
            return '{"message": "Sorry, something went wrong.", "topic_score": 0}'

# Register the model and admin class
admin.site.register(DigitalMarketing, DigitalMarketingAdmin)

from django.contrib import admin
from .models import ChatHistory, Course, Lesson, LessonProgress


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'lesson', 'timestamp')
    list_filter = ('lesson', 'timestamp')
    search_fields = ('user__username', 'message', 'reply')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('name', 'order', 'description')
    ordering = ('order',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    inlines = [LessonInline]  # Inline lessons for a course


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('name', 'course__name')
    ordering = ('order',)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'lesson', 'completed', 'completed_at')
    list_filter = ('course', 'completed', 'completed_at')
    search_fields = ('user__username', 'course__name', 'lesson__name')
    readonly_fields = ('completed_at',)
    list_editable = ('completed',)
