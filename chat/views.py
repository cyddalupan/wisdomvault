import os
import json
import traceback
import requests
from django.utils import timezone
from datetime import timedelta
from openai import OpenAI
from django.http import JsonResponse, HttpResponse
from chat import utils
from chat.functions import analyze, handle_image, inventory, leads, other, schedule, schedule_admin, customer, help, escalate
from chat.functions.categorizer import getCategory, topic_description
from chat.functions.cron_sheet_cleaner import process_sales
from chat.functions.get_name import bypass_get_name
from chat.task_queue import enqueue_task
from chat.toolcall import trigger_tool_calls
from page.models import FacebookPage
from .models import Chat, UserProfile
from chat.utils import escalate_function, escalate_master, getChatHistory, send_image, send_message, escalate_normal, escalate_bad
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')

def index(request):
    return render(request, 'index.html')

@csrf_exempt
def save_facebook_chat(request):
    if request.method == 'GET':
        # ... existing GET code unchanged ...
        if request.GET.get('hub.verify_token') == VERIFY_TOKEN:
            return HttpResponse(request.GET['hub.challenge'])
        return HttpResponse('Invalid token', status=403)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Malformed JSON'}, status=400)

        for entry in data['entry']:
            for event in entry['messaging']:
                sender_id = event['sender']['id']
                page_id = entry['id']

                try:
                    facebook_page_instance = FacebookPage.objects.get(page_id=page_id)
                except FacebookPage.DoesNotExist:
                    return JsonResponse({'error': 'Page not found'}, status=404)

                user_profile, created = UserProfile.objects.get_or_create(
                    facebook_id=sender_id,
                    defaults={
                        'facebook_id': sender_id,
                        'page_id': page_id,
                        'user_type': 'customer',
                        'task': 'customer',
                    }
                )

                message = event.get('message', {})
                message_text = message.get('text')

                if 'attachments' in message:
                    handle_image(message, user_profile, sender_id, facebook_page_instance)
                elif message_text:
                    chat = Chat.objects.create(user=user_profile, message=message_text, reply='')

                    # Queue the processing function asynchronously
                    def async_process():
                        response_text, triggered_function = process_ai_response(user_profile, facebook_page_instance, True)
                        send_message(sender_id, response_text, facebook_page_instance)
                        if triggered_function:
                            chat.refresh_from_db()
                        chat.reply = response_text
                        chat.save()
                        return JsonResponse({'status': 'message processed', 'reply': response_text}, status=200)

                    enqueue_task(async_process)

        return JsonResponse({'status': 'message processed', 'reply': "WAIT"}, status=200)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

def process_ai_response(user_profile, facebook_page_instance, first_run):
    triggered_function = False
    chat_history = getChatHistory(user_profile)

    # Initial empty instruction and tools setup
    def instruction(facebook_page_instance):
        return ""
    
    current_instruction = instruction
    tools = []
    tool_function = None

    # change task to customer when empty.
    if not user_profile.task:
        user_profile.task = "customer"
        user_profile.save()

    # Bypass All to get name
    if not user_profile.name:
        get_name_response = bypass_get_name(chat_history, user_profile)
        if get_name_response:
            return get_name_response, False

    # Determine the task and set up instructions, tools, and functions
    if user_profile.user_type == 'admin':
        # Escalete before anything else
        activeHelp =  escalate.isThereQuestion(facebook_page_instance)
        if activeHelp:
            return escalate.bypass(activeHelp, chat_history, user_profile, facebook_page_instance), False

        getCategory(user_profile, chat_history, facebook_page_instance)

        if user_profile.task == "inventory" or user_profile.task == "sales" :
            current_instruction = inventory.instruction
            tools = inventory.generate_tools()
            tool_function = inventory.tool_function
        elif user_profile.task == "other":
            current_instruction = other.instruction
            tools = other.generate_tools()
            tool_function = other.tool_function
        elif user_profile.task == "analyze":
            current_instruction = analyze.instruction
            tools = analyze.generate_tools()
            tool_function = analyze.tool_function
        elif user_profile.task == "schedule":
            current_instruction = schedule_admin.instruction
            tools = schedule_admin.generate_tools()
            tool_function = schedule_admin.tool_function
    if user_profile.user_type == 'customer':
        current_instruction = customer.instruction
        
        if facebook_page_instance.is_online_selling:
            tools = customer.generate_tools()
        tool_function = customer.tool_function
        # All Leads Info
        leads_instruction = ""
        if facebook_page_instance.is_leads and not user_profile.is_leads_complete:
            leads_instruction = leads.instruction()
            tools.append(leads.generate_tools())

        # All schedule Info
        schedule_instruction = ""
        if facebook_page_instance.is_scheduling:
            schedule_instruction = schedule.instruction(facebook_page_instance, user_profile.facebook_id)
            schedule_tool = schedule.generate_tools(facebook_page_instance, user_profile.facebook_id)
            if schedule_tool is not None:
                tools.append(schedule_tool)

    # Build AI message with instruction based on task
    if user_profile.user_type == "admin":
        current_task = user_profile.task.lower()  # Current task from user_profile
        topic_instruction = current_instruction(facebook_page_instance)  # Get business-related info based on current task

        # Prepare the system message dynamically with the current task and topic-specific instructions
        messages = [
            {
                "role": "system",
                "content": (
                    f"Your name is KENSHI short for (Kiosk and Easy Navigation System for Handling Inventory). "
                    f"Speak in taglish, keep replies short, No markdown just emoji and proper spacing, and focus STRICTLY on the current topic: '{current_task}'. "
                    f"be more casual, use 'po', 'opo', sir or maam. "
                    f"Full Details of current topic: ({topic_instruction}) "
                    # List topic informations.
                    f"{topic_description(facebook_page_instance)}"
                )
            }
        ]

    if user_profile.user_type == "customer":
        messages = [
            {
                "role": "system",
                "content": (
                    leads_instruction
                    + (
                        "Your name is KENSHI short for 'Kiosk and Easy Navigation System for Handling Inventory'. "
                        "Speak in taglish, keep replies short, No markdown just emoji and proper spacing. "
                        "Dominate the conversation and avoid asking what user wants, instead suggest what they need. "
                        "be more casual, use 'po', 'opo', sir or maam. know the customer and use emotion to sell. "
                        + ("Your purpose is to assist customers with inquiries about products, promotions, pricing, inventory, and other business-related topics. " if facebook_page_instance.is_inventory else "")
                        + "STRICTLY base your answers ONLY on the 'Information' and 'Additional Info' provided. "
                        "NEVER guess, assume, or invent answers. "
                        "If a customer asks a question unrelated to the business, politely redirect them to focus on business-related topics only. "
                        "If a customer asks a business-related question and the answer is not found in the 'Information' and 'Additional Info', unclear or incomplete, IMMEDIATELY trigger the 'ask_manager_help' tool function to ask the admin/owner/manager for clarification. "
                        "Never apologize instead ask manager using tool function 'ask_manager_help'. "
                        "Under NO circumstances should you assume, invent, or provide information that is not explicitly found in the 'Information' and 'Additional Info'.\n\n"
                    )
                    + current_instruction(facebook_page_instance)
                    + (schedule_instruction if not leads_instruction else "")
                ),
            }
        ]

    if user_profile.summary:
        summary_message = {
            "role": "system",  # Set to "user" if the message needs to be from the user
            "content": f"Here is the conversation summary for the user: '{user_profile.summary}'"
        }

        # Append the summary message to the list of messages
        messages.append(summary_message)

    # Include previous chat history in the conversation
    for chat in chat_history:
        if chat.message and chat.message != "":
            messages.append({"role": "user", "content": chat.message})
        if chat.reply and chat.reply != "":
            messages.append({"role": "assistant", "content": chat.reply})
    
    # Add tool for customer when the system does not know what to say
    if first_run and user_profile.user_type != 'admin':
        tools = tools or []  # Ensure tools is initialized if None
        tools.append(help.generate_tools())

    # Attempt to generate a completion using the OpenAI API
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=1,
            tools=tools
        )
        response_content = completion.choices[0].message.content

        # Handle tool calls if present
        tool_calls = completion.choices[0].message.tool_calls
        if tool_calls:
            completion2 = escalate_function(messages, tools)
            tool_calls2 = completion2.choices[0].message.tool_calls
            
            try:
                if not tool_calls2 or (tool_calls[0].function != tool_calls2[0].function):            
                    completion = escalate_master(messages, tools, tool_calls[0].function, tool_calls2[0].function)
                    response_content = completion.choices[0].message.content
                    # Handle tool calls if present
                    tool_calls = completion.choices[0].message.tool_calls
            except (IndexError, AttributeError):
                # Handle the case where the list is empty or the attribute is missing
                pass
            if tool_calls:
                triggered_function = True
                response_content = trigger_tool_calls(first_run, tool_calls, user_profile, facebook_page_instance, tool_function)
        else:
            messages.append({
                "role": "assistant",
                "content": response_content
            })
            escalate_result = escalate_normal(messages)
            if escalate_result == "BAD":
                completion = escalate_bad(messages, tools)
                response_content = completion.choices[0].message.content

                # Handle tool calls if present
                tool_calls = completion.choices[0].message.tool_calls
                if tool_calls:
                    response_content = trigger_tool_calls(first_run, tool_calls, user_profile, facebook_page_instance, tool_function)
            if not response_content and first_run:
                # Retry the process if tool function fails during the first run
                response_content, triggered_function = process_ai_response(user_profile, facebook_page_instance, False)
            if not first_run:
                # Send an apology if retries fail
                response_content = "I am sorry it seems like I am getting confused. Can we try again?"

    except requests.exceptions.Timeout:
        # Handle timeout errors specifically
        response_content = "The system is currently busy. Please try again in a moment."

    except requests.exceptions.RequestException as e:
        # Handle connectivity or request-related errors
        response_content = "There seems to be a connectivity issue. Please check your connection or try again later."

    except Exception as e:
        # Log unexpected exceptions for debugging
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        response_content = (
            "The system is currently unavailable due to unexpected issues. "
            "Our team is working to resolve this. Please try again later."
        )

    return response_content, triggered_function

def get_users_for_follow_up(hours=6):
    start_time = timezone.now() - timedelta(hours=hours + 1)  # From one hour before 6 hours ago
    end_time = timezone.now() - timedelta(hours=hours)  # Up to exactly 6 hours ago

    users = UserProfile.objects.filter(
        is_leads_complete=False,
        chat__timestamp__range=(start_time, end_time),
    ).exclude(chat__message='').distinct()

    return users

def my_cron_view(request):
    users = get_users_for_follow_up(6)

    for user in users:
        page_instance = FacebookPage.objects.filter(page_id=user.page_id).first()
        
        if page_instance:
            response_text = "🌟 Hey there! Let's complete your info so we can contact you! 😊"
            send_message(user.facebook_id, response_text, page_instance)
            Chat.objects.create(user=user, message='', reply=response_text)

    return HttpResponse("Messages sent successfully!")

def cron_sheet_cleaner(request):
    all_pages = FacebookPage.objects.all()
    for page in all_pages:
        process_sales(page.sheet_id)

    return HttpResponse("Sheets Updated!")

def chat_test_page(request):
    return render(request, 'chat_test.html')


def function_tester(request):
    facebook_page_instance = FacebookPage.objects.get(page_id="123456789")
    bookings = schedule_admin.latest_data(facebook_page_instance)
    
    # Return a simple HTTP response to confirm it worked
    return HttpResponse("Inventory setup function executed successfully.")
