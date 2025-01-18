import os
import json
import traceback
import requests
from openai import OpenAI
from django.http import JsonResponse, HttpResponse
from chat.functions import change_topic, inventory, inventory_setup, other, pos, verify_user, customer, help, escalate
from chat.functions.task_utils import identify_task
from page.models import FacebookPage
from .models import Chat, UserProfile
from chat.utils import send_message
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
        # Verify the webhook setup with Facebook
        if request.GET.get('hub.verify_token') == VERIFY_TOKEN:
            return HttpResponse(request.GET['hub.challenge'])
        return HttpResponse('Invalid token', status=403)

    elif request.method == 'POST':
        data = json.loads(request.body)
        response_text = ""

        for entry in data['entry']:
            for event in entry['messaging']:
                sender_id = event['sender']['id']  # The user's Facebook ID
                page_id = entry['id']  # The Facebook page ID
                message_text = event['message'].get('text')  # Message text sent by the user

                if message_text:
                    # Create or retrieve the user profile
                    user_profile, created = UserProfile.objects.get_or_create(
                        facebook_id=sender_id,
                        defaults={
                            'facebook_id': sender_id,
                            'page_id': page_id,
                            'user_type': 'customer',
                            'task': 'customer',
                        }
                    )

                    # Identify the user's task based on the message
                    identified_task = identify_task(message_text)
                    if identified_task:
                        user_profile.task = identified_task
                        user_profile.save()

                    # Save the incoming message to the Chat model
                    chat = Chat.objects.create(user=user_profile, message=message_text, reply='')

                    # Fetch the FacebookPage instance
                    facebook_page_instance = FacebookPage.objects.get(page_id=user_profile.page_id)

                    # Process the AI response based on the user's profile and task
                    response_text = ai_process(user_profile, facebook_page_instance, True)

                    # Send the AI-generated response back to the user
                    send_message(sender_id, response_text, facebook_page_instance)

                    # Save the reply to the Chat model
                    chat.reply = response_text
                    chat.save()
        return JsonResponse({'status': 'message processed', 'reply': response_text}, status=200)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def ai_process(user_profile, facebook_page_instance, first_run):
    # Retrieve the last 12 chat history for this user
    chat_history = Chat.objects.filter(user=user_profile).order_by('-timestamp')[:12]
    chat_history = list(chat_history)[::-1]  # Reverse to maintain correct chronological order

    # Initial empty instruction and tools setup
    def instruction(facebook_page_instance):
        return ""
    
    instruction = instruction
    tools = None
    tool_function = None

    # change task to customer when empty.
    if not user_profile.task:
        user_profile.task == "customer"
        user_profile.save()

    # Determine the task and set up instructions, tools, and functions
    if user_profile.user_type == 'admin':
        # Make sure there are no escalation at the moment
        instruction = escalate.instruction
        tools = escalate.generate_tools()
        tool_function = escalate.tool_function
        if not instruction:
            if user_profile.task == "verify_user":
                instruction = verify_user.instruction
                tools = verify_user.generate_tools()
                tool_function = verify_user.tool_function
            elif user_profile.task == "inventory_setup":
                instruction = inventory_setup.instruction
                tools = inventory_setup.generate_tools()
                tool_function = inventory_setup.tool_function
            elif user_profile.task == "inventory":
                instruction = inventory.instruction
                tools = inventory.generate_tools()
                tool_function = inventory.tool_function
            elif user_profile.task == "other":
                instruction = other.instruction
                tools = other.generate_tools()
                tool_function = other.tool_function
            elif user_profile.task == "pos":
                instruction = pos.instruction
                tools = pos.generate_tools()
                tool_function = pos.tool_function
    if user_profile.user_type == 'customer':
        if user_profile.task == "customer":
            instruction = customer.instruction
            tools = customer.generate_tools()
            tool_function = customer.tool_function

    # Build AI message with instruction based on task
    messages = [
        {"role": "system", "content": "Your name is KENSHI (Kiosk and Easy Navigation System for Handling Inventory). Talk in taglish. Keep reply short. Go straight to the point. Focus only on: " + instruction(facebook_page_instance)}
    ]

    # Include previous chat history in the conversation
    for chat in chat_history:
        if chat.message and chat.message != "":
            messages.append({"role": "user", "content": chat.message})
        if chat.reply and chat.reply != "":
            messages.append({"role": "assistant", "content": chat.reply})

    # Add tool for changing topic if user is admin or user is not customer
    if first_run and user_profile.user_type == 'admin':
        tools = tools or []  # Ensure tools is initialized if None
        tools.append(change_topic.generate_tools())
    
    # Add tool for customer when the system does not know what to say
    if first_run and (user_profile.user_type != 'admin'):
        tools = tools or []  # Ensure tools is initialized if None
        tools.append(help.generate_tools())

    # Attempt to generate a completion using the OpenAI API
    print("messages", messages)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )
        response_content = completion.choices[0].message.content

        # Handle tool calls if present
        tool_calls = completion.choices[0].message.tool_calls
        print("tool_calls", tool_calls)
        if tool_calls:
            if any(tool_call.function.name == "change_topic" for tool_call in tool_calls):
                response_content = change_topic.tool_function(tool_calls, user_profile)
            if any(tool_call.function.name == "help" for tool_call in tool_calls):
                response_content = help.tool_function(tool_calls, user_profile)
            else:
                response_content = tool_function(tool_calls, user_profile, facebook_page_instance)

            if not response_content and first_run:
                # Retry the process if tool function fails during the first run
                response_content = ai_process(user_profile, facebook_page_instance, False)
            if not first_run:
                # Send an apology if retries fail
                response_content = "I am sorry it seems like I am getting confused. Can we start again?"

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
    
    return response_content

def chat_test_page(request):
    return render(request, 'chat_test.html')


def function_tester(request):
    # Call the inventory setup function
    inventory_setup.format_sheets("1u-Vy9b3KD4l3Ne2ZM3DXg8NmPxzv_QHJzXtzVPKeHu8")
    
    # Return a simple HTTP response to confirm it worked
    return HttpResponse("Inventory setup function executed successfully.")