import json
import logging
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from .models import Angular, DigitalMarketing, Python, SoftwareQa, Lawyer
from .forms import LearnHubForm
from openai import OpenAI
from dotenv import load_dotenv
from .models import ChatHistory, Course, Lesson, LessonProgress

load_dotenv()

client = OpenAI()

def learn_hub(self, request, course):
    user_profile = request.user
    form = LearnHubForm(request.POST or None)
    ai_response = ''
    latest_learn_hub = None
    user_progress = None
    message = ""
    topic_score = 0
    overall_score = 1
    
    # Get all lesson from the course
    lessons = Lesson.objects.filter(course=course).order_by('order')
    total_lessons = lessons.count()
    user_progress = LessonProgress.objects.filter(user=user_profile, course=course).first()
    
    if user_progress:
        current_lesson_order = user_progress.lesson.order
    else:
        current_lesson_order = 0 
    if total_lessons > 0:
        overall_score = (current_lesson_order / total_lessons) * 95

    learn_hub_instance = form.save(commit=False)

    if request.method == 'POST' and form.is_valid():
        # Call the AI function with user input and course details
        response_json = perform_learn_hub(
            self, learn_hub_instance.user_input, user_profile, course
        )
        
        if not response_json:
            response_json = '{"message": "No response received.", "topic_score": 0}'

        # Parse the JSON response string
        response_data = json.loads(response_json)

        # Extract json
        message = response_data.get('message', '')
        topic_score = response_data.get('topic_score', 0)

        # Ensure topic_score is treated as a number
        if isinstance(topic_score, str):  
            topic_score = float(topic_score)
        
        if topic_score >= 95 and (user_progress and not user_progress.completed):
            if user_progress:
                # Get the next lesson based on the order
                next_lesson = lessons.filter(order__gt=user_progress.lesson.order).first()

                if next_lesson:
                    # Update user progress to the next lesson
                    user_progress.lesson = next_lesson
                    user_progress.completed = False
                    user_progress.save()
                    topic_score = 1
                else:
                    # If no more lessons, (user has completed the course)
                    user_progress.completed = True
                    user_progress.save()

        # Store the message
        learn_hub_instance.ai_response = message

        # Save the instance
        learn_hub_instance.save()

        # Use formatted output for rendering
        ai_response = learn_hub_instance.formatted_output
    else:
        # Load the latest digital marketing instance for display if it exists
        if DigitalMarketing.objects.exists():
            latest_learn_hub = DigitalMarketing.objects.latest('id')
            if user_progress:
                last_chat = ChatHistory.objects.filter(user=user_profile, lesson=user_progress.lesson).order_by('-timestamp').first()
                if last_chat:
                    response_data = json.loads(last_chat.reply)
                    message = response_data.get('message', '')
                    topic_score = response_data.get('topic_score', 0)
                    learn_hub_instance.ai_response = message
                    ai_response = learn_hub_instance.formatted_output

    # Empty input text value
    form = LearnHubForm()

    # Pass context to the template
    context = dict(
        self.admin_site.each_context(request),
        form=form,
        ai_response=ai_response,
        topic_score=round(topic_score),
        overall_score=round(overall_score),
        latest_learn_hub=latest_learn_hub,
    )
    
    # Print done when done
    if user_progress and user_progress.completed:
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            ai_response="Congratulations",
            topic_score=100,
            overall_score=100,
            latest_learn_hub=latest_learn_hub,
        )
    return render(request, "admin/learnhub.html", context)

def perform_learn_hub(self, text, user_profile, course):
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
        print(f"Error in AI response: {e}")
        # Return a fallback JSON if there's an error
        return '{"message": "Sorry, something went wrong.", "topic_score": 0}'

# Digital Marketing Page
class DigitalMarketingAdmin(admin.ModelAdmin):
    change_list_template = "admin/learnhub.html"
    def changelist_view(self, request, extra_context=None):
        course_name = "Digital Marketing"
        course = Course.objects.filter(name=course_name).first()
        return learn_hub(self, request, course)
# Register the model and admin class
admin.site.register(DigitalMarketing, DigitalMarketingAdmin)


# Python Page
class PythonAdmin(admin.ModelAdmin):
    change_list_template = "admin/learnhub.html"
    def changelist_view(self, request, extra_context=None):
        course_name = "Python"
        course = Course.objects.filter(name=course_name).first()
        return learn_hub(self, request, course)
# Register the model and admin class
admin.site.register(Python, PythonAdmin)


# Software QA
class SoftwareQaAdmin(admin.ModelAdmin):
    change_list_template = "admin/learnhub.html"
    def changelist_view(self, request, extra_context=None):
        course_name = "Software QA"
        course = Course.objects.filter(name=course_name).first()
        return learn_hub(self, request, course)
# Register the model and admin class
admin.site.register(SoftwareQa, SoftwareQaAdmin)


# Angular
class AngularAdmin(admin.ModelAdmin):
    change_list_template = "admin/learnhub.html"
    def changelist_view(self, request, extra_context=None):
        course_name = "Angular"
        course = Course.objects.filter(name=course_name).first()
        return learn_hub(self, request, course)
# Register the model and admin class
admin.site.register(Angular, AngularAdmin)

# Lawyer
class LawyerAdmin(admin.ModelAdmin):
    change_list_template = "admin/lawyer.html"
    def changelist_view(self, request, extra_context=None):
        course_name = "Lawyer"
        course = Course.objects.filter(name=course_name).first()
        return learn_hub(self, request, course)
# Register the model and admin class
admin.site.register(Lawyer, LawyerAdmin)



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
    list_display = ('id', 'user', 'course', 'lesson', 'completed')
    list_filter = ('course', 'completed')
    search_fields = ('user__username', 'course__name', 'lesson__name')
    list_editable = ('completed',)
