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
            user_profile = request.user
            # TODO: Update getting course
            course = Course.objects.first()
            digital_marketing_instance.ai_response = self.perform_digital_marketing(
                digital_marketing_instance.user_input, user_profile, course
            )
            # TODO: perform_digital_marketing will return the json format but I need to only pass and display the message. 
            # plus the json is a string a the moment so we need some adjustments
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
                "content": f"""
                    first you are an API that returns json with format {{message: 'actual message here, can be markdown', topic_score: 1-100}}.
                    second you are a teacher teaching the user about {course}, but focusing on the topic: {lesson}.
                    You will occasionally give quizzes and score the user's mastery of the topic (focus score on the topic/lesson only). 
                    Be strict in scoring and ensure the user is not cheating.
                """
            },
        ]

        
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

            latest_chat.reply = ai_reply
            latest_chat.save()
            return ai_reply
        except Exception as e:
            raise e

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
