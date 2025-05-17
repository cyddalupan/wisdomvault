import json
import logging
import ast
import re
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from .models import Angular, DigitalMarketing, Htmlcss, Phplang, Python, SoftwareQa, Lawyer, Tableau
from .forms import LearnHubForm
from openai import OpenAI
from dotenv import load_dotenv
from .models import ChatHistory, Course, Lesson, LessonProgress

load_dotenv()

client = OpenAI()

def learn_hub(self, request, course):
    user_profile = request.user
    form = LearnHubForm(request.POST or None)
    ai_response_html = ''
    latest_learn_hub = None
    user_progress = None
    topic_score = 0
    overall_score = 1

    # Fetch lessons & progress
    lessons = Lesson.objects.filter(course=course).order_by('order')
    total_lessons = lessons.count()
    user_progress = LessonProgress.objects.filter(
        user=user_profile, course=course
    ).first()

    current_order = (
        user_progress.lesson.order
        if user_progress and user_progress.lesson and hasattr(user_progress.lesson, 'order')
        else 0
    )
    if total_lessons > 0:
        overall_score = (current_order / total_lessons) * 95

    learn_hub_instance = form.save(commit=False)

    def parse_response(raw_response):
        """
        Try to parse the AI’s reply as JSON.  If that fails,
        fall back to a minimal regex (or just return a default).
        """
        try:
            # If it’s bytes, decode it
            if isinstance(raw_response, bytes):
                raw_response = raw_response.decode('utf-8')

            # Strip any surrounding backticks or markdown fences
            raw_response = raw_response.strip().lstrip('```').rstrip('```').strip()

            # Load it as JSON
            data = json.loads(raw_response)

            # Pull out message and topic_score
            message = data.get('message', '')
            topic_score = data.get('topic_score', 0)

            return {
                'message': message,
                'topic_score': topic_score
            }

        except json.JSONDecodeError as e:
            # If the AI sometimes returns non-JSON junk,
            # you can fall back to your old regex or just return a default
            print(f"JSON decode failed: {e}")
            # -- minimal regex fallback if you must:
            m = re.search(r'"message"\s*:\s*"(.*?)"\s*,', raw_response, re.DOTALL)
            s = re.search(r'"topic_score"\s*:\s*(\d+)', raw_response)
            return {
                'message': m.group(1).replace('\\n','\n').replace('\\"','"') if m else 'Parsing error',
                'topic_score': int(s.group(1)) if s else 0
            }
        except Exception as e:
            print(f"Unexpected error in parse_response: {e}")
            return {'message': 'Parsing error', 'topic_score': 0}

    if request.method == 'POST' and form.is_valid():
        # call the AI
        response_json = perform_learn_hub(
            self, learn_hub_instance.user_input, user_profile, course
        ) or '{"message": "No response received.", "topic_score": 0}'

        rd = parse_response(response_json)
        message = rd['message']
        topic_score = float(rd['topic_score'])

        # advance the lesson if they scored ≥95
        if topic_score >= 95 and user_progress and not user_progress.completed:
            nxt = lessons.filter(order__gt=user_progress.lesson.order).first()
            if nxt:
                user_progress.lesson = nxt
                user_progress.completed = False
            else:
                user_progress.completed = True
            user_progress.save()

        # **treat AI message as HTML directly**
        learn_hub_instance.ai_response = message
        learn_hub_instance.ai_response_html = message  # no markdown conversion
        learn_hub_instance.save()

        ai_response_html = message

    else:
        # on GET, show last saved chat if present
        if DigitalMarketing.objects.exists():
            latest_learn_hub = DigitalMarketing.objects.latest('id')
            if user_progress:
                last = ChatHistory.objects.filter(
                    user=user_profile, lesson=user_progress.lesson
                ).order_by('-timestamp').first()
                if last:
                    rd = parse_response(last.reply)
                    message = rd['message']
                    learn_hub_instance.ai_response = message
                    learn_hub_instance.ai_response_html = message
                    ai_response_html = message

    # reset form
    form = LearnHubForm()

    # build context
    context = {
        **self.admin_site.each_context(request),
        'form': form,
        'ai_response_html': ai_response_html,
        'topic_score': round(topic_score),
        'overall_score': round(overall_score),
        'latest_learn_hub': latest_learn_hub,
    }

    # if course complete, override with congratulations
    if user_progress and user_progress.completed:
        context.update({
            'ai_response_html': '<h2>Congratulations!</h2><p>You have completed this course.</p>',
            'topic_score': 100,
            'overall_score': 100,
        })

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
    chat_history = ChatHistory.objects.filter(user=user_profile, lesson=lesson).order_by('-timestamp')[:10]
    chat_history = list(chat_history)[::-1]

    messages = [
        {
            "role": "system", 
            "content": (
                f"Teach users {course} by introducing foundational concepts for the topic: {lesson.name}. "
                "Use Taglish and English based on the user's language preference. "
                "Implement a cycle of teaching, gauging understanding, and answering questions about this topic.\n\n"
                "# Steps\n\n"
                "- Start by presenting fundamental aspects of the topic.\n"
                "- Every third interaction, include a gauging method (quiz, essay, or coding task) on previously taught topics to assess understanding.\n"
                "- Provide clear, constructive feedback to adjust the user's topic score fairly and strictly.\n"
                "- Use FontAwesome and Bootstrap for visual and instructional clarity in all replies.\n\n"
                "# Output Format\n\n"
                "Produce the output in the following JSON format, containing the HTML message styled with Bootstrap and FontAwesome, along with the topic score:\n\n"
                "{\n"
                "  \"message\": \"HTML message styled with Bootstrap and FontAwesome here.\",\n"
                "  \"topic_score\": 0\n"
                "}\n"
                "\n\n"
                "The HTML should include:\n\n"
                "- **Message**: Use Bootstrap and FontAwesome to present the instructional content engagingly. Paragraphs should cover teaching points with visual components, always specific to {lesson.name}.\n"
                "- **Topic Score**: 1 to 100 on how much the user is familiar with the topic.\n\n"
                "# Examples\n\n"
                "Here’s how an example output could be structured:\n\n"
                "{\n"
                "  \"message\": \"<div class=\\\"container mt-5\\\"><h3 class=\\\"mb-3\\\"><i class=\\\"fas fa-chart-line\\\"></i> Understanding {lesson.name}</h3>"
                "<p>We’ve covered key aspects of {lesson.name}: how to define it, its purpose, and common patterns. Keep practicing to deepen your grasp.</p></div>"
                "  \"topic_score\": 30\n"
                "}\n"
                "\n\n"
                "# Wrong Output"
                "```json\n"
                "{\n"
                "  \"message\": \"HTML message styled with Bootstrap and FontAwesome here.\",\n"
                "  \"topic_score\": 0\n"
                "}\n"
                "```\n\n"
                "IMPORTANT: output should not have '```' or should not have a markdown"
                "# Notes\n\n"
                "- Use both FontAwesome and Bootstrap for a visually appealing presentation.\n"
                "- Begin with a topic score of 1, only increasing as the user demonstrates knowledge and skill. Mastery/expertise is achieved at a topic score of 100.\n"
                "- Remain supportive and always provide honest, fair, and sometimes strict improvement advice based on assessments.\n"
                "- Do not restrict output; design and layout may change based on different teaching scenarios.\n"
                "- Always tailor teaching, assessment, and examples to the current topic: {lesson.name}."
                + (f"\nAdditional topic information: {lesson.description}." if lesson.description else "")
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
            model="gpt-4.1-mini",
            temperature=0,
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


class HtmlcssAdmin(admin.ModelAdmin):
    change_list_template = "admin/learnhub.html"
    def changelist_view(self, request, extra_context=None):
        course_name = "HTML and CSS"
        course = Course.objects.filter(name=course_name).first()
        return learn_hub(self, request, course)
# Register the model and admin class
admin.site.register(Htmlcss, HtmlcssAdmin)


class TableauAdmin(admin.ModelAdmin):
    change_list_template = "admin/learnhub.html"
    def changelist_view(self, request, extra_context=None):
        course_name = "Tableau"
        course = Course.objects.filter(name=course_name).first()
        return learn_hub(self, request, course)
# Register the model and admin class
admin.site.register(Tableau, TableauAdmin)

class PhplangAdmin(admin.ModelAdmin):
    change_list_template = "admin/learnhub.html"
    def changelist_view(self, request, extra_context=None):
        course_name = "PHP Programming"
        course = Course.objects.filter(name=course_name).first()
        return learn_hub(self, request, course)
# Register the model and admin class
admin.site.register(Phplang, PhplangAdmin)

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
    change_list_template = "admin/learnhub.html"
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
