from django.contrib import admin
from .models import Assistant, ChatHistory, Tableau
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

class AssistantAdmin(admin.ModelAdmin):
    list_display = ('name', 'instruction')
    search_fields = ('name',)

class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('assistant', 'user', 'message', 'reply', 'timestamp')
    search_fields = ('message', 'reply')
    list_filter = ('assistant', 'user', 'timestamp')

admin.site.register(Assistant, AssistantAdmin)
admin.site.register(ChatHistory, ChatHistoryAdmin)

def get_context(assistant_name, request, extra_context=None):
    extra_context = extra_context or {}

    assistant = Assistant.objects.filter(name=assistant_name).first()
    user_profile = request.user

    if request.method == 'POST' and assistant is not None:
        if 'clear_chat' in request.POST:
            # Clear the chat history for the user and assistant
            ChatHistory.objects.filter(user=user_profile, assistant=assistant).delete()
            extra_context['chat_history'] = []  # Reset the chat history in the context
            return extra_context
        else:
            message = request.POST.get('chat_message', '')

            chat_history = ChatHistory.objects.filter(user=user_profile, assistant=assistant).order_by('-timestamp')[:20]
            chat_history = list(chat_history)[::-1]

            messages = [
                {
                    "role": "system", 
                    "content": assistant.instruction
                }
            ]

            chat_pairs = []
            for chat in chat_history:
                chat_pairs.append({'role': 'user', 'content': chat.message})
                if chat.reply and chat.reply != "":
                    chat_pairs.append({'role': 'assistant', 'content': chat.reply})
            chat_pairs.append({"role": "user", "content": message})

            # Extend messages with chat_pairs
            messages.extend(chat_pairs)

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            ai_reply = completion.choices[0].message.content

            # Push reply to chat_pairs so it is included when printing chat history
            chat_pairs.append({"role": "assistant", "content": ai_reply})

            # Save DB
            ChatHistory.objects.create(
                assistant=assistant,
                user=user_profile, 
                message=message,
                reply=ai_reply
            )

            extra_context['chat_history'] = chat_pairs
    else:
        chat_history = ChatHistory.objects.filter(user=user_profile, assistant=assistant).order_by('-timestamp')[:20]
        chat_history = list(chat_history)[::-1]
        chat_pairs = []
        for chat in chat_history:
            chat_pairs.append({'role': 'user', 'content': chat.message})
            if chat.reply and chat.reply != "":
                chat_pairs.append({'role': 'assistant', 'content': chat.reply})
        extra_context['chat_history'] = chat_pairs

    return extra_context

class TableauAdmin(admin.ModelAdmin):
    change_list_template = "admin/chat_template.html"

    def changelist_view(self, request, extra_context=None):
        model = "Tableau"
        extra_context = get_context(model, request, extra_context)
        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(Tableau, TableauAdmin)