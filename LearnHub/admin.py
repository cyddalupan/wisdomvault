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
    chat_history = ChatHistory.objects.filter(user=user_profile, lesson=lesson).order_by('-timestamp')[:20]
    chat_history = list(chat_history)[::-1]

    messages = [
        {
            "role": "system", 
            "content": (
                f"Guide users in learning {course}, focusing on the topic: {lesson.name}. "
                "Mix Taglish and English, adapting to the user's language preference. "
                "Every third conversation should include a gauging method (quiz, essay, or coding task) to assess understanding. "
                "Fair and strict evaluation is crucial for honesty and improvement. "
                "Begin with a topic score of 1, adjusting as the user's performance and knowledge grow, ensuring expertise before reaching a score of 100. "
                "Your role is to facilitate discussion, not just pose questions.\n\n"
                "# Steps\n\n"
                "- Assess the user during every third interaction with an appropriate gauging method.\n"
                "- Evaluate the user's knowledge strictly to adjust the topic score.\n"
                "- Use conversation primarily to guide, instruct, and ensure learning progression.\n\n"
                "# Output Format\n\n"
                "Produce the output in the following JSON format, containing the HTML Bootstrap message and topic score:\n\n"
                "```json\n"
                "{\n"
                "  \"message\": \"html bootstrap message here.\",\n"
                "  \"topic_score\": 0\n"
                "}\n"
                "```\n\n"
                "The HTML should include:\n\n"
                "- **Message**: Paragraphs containing the instructional message. Convert any markdown elements into HTML using Bootstrap.\n"
                "- **Topic Score**: Include the topic score as a Bootstrap-styled component, such as a progress bar.\n\n"
                "# Examples\n\n"
                "Consider using Bootstrap-based elements for your HTML output. Adjust design elements as needed based on scenario specifics. Here's an example:\n\n"
                "```json\n"
                "{\n"
                "  \"message\": \"<div class=\\\"container mt-5\\\"><h3 class=\\\"mb-3\\\">Understanding {lesson.name}</h3>"
                "<p>We’ve covered key aspects of {lesson.name}: how to define it, its purpose, and common patterns. Keep practicing to deepen your grasp.</p>"
                "<div class=\\\"progress\\\"><div class=\\\"progress-bar\\\" role=\\\"progressbar\\\" style=\\\"width: 30%;\\\""
                " aria-valuenow=\\\"30\\\" aria-valuemin=\\\"0\\\" aria-valuemax=\\\"100\\\">30%</div></div></div>\",\n"
                "  \"topic_score\": 30\n"
                "}\n"
                "```\n\n"
                "# Notes\n\n"
                "- Ensure the HTML elements use Bootstrap for styling.\n"
                "- Keep communication engaging and supportive.\n"
                "- Do not limit the output; allow for design adjustments depending on scenarios.\n"
                "- This is an api so Ensure the output format is {'message': 'html bootstrap here', 'topic_score': <score here>}.\n"
                + (f"Additional topic information: {lesson.description}. " if lesson.description else "")
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
            model="o4-mini",
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
