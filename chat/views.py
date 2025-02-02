import os
import json
import traceback
import requests
from openai import OpenAI
from django.http import JsonResponse, HttpResponse
from chat import utils
from chat.functions import analyze, change_topic, inventory, inventory_setup, other, pos, verify_user, customer, help, escalate
from chat.functions.task_utils import identify_task
from page.models import FacebookPage
from .models import Chat, UserProfile
from chat.utils import get_facebook_user_name, get_possible_topics, send_image, topic_description, send_message, summarizer
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
                # Fetch the FacebookPage instance
                facebook_page_instance = FacebookPage.objects.get(page_id=page_id)
                # Create or retrieve the user profile
                user_profile, created = UserProfile.objects.get_or_create(
                    facebook_id=sender_id,
                    defaults={
                        'facebook_id': sender_id,
                        'page_id': page_id,
                        'name': get_facebook_user_name(sender_id, facebook_page_instance.token),
                        'user_type': 'customer',
                        'task': 'customer',
                    }
                )
                message_text = event['message'].get('text')  # Message text sent by the user

                 # Check for image attachment
                if 'attachments' in event['message']:
                    for attachment in event['message']['attachments']:
                        if attachment['type'] == 'image':
                            image_url = attachment['payload']['url']
                            message_text = "[User Sends Image]"
                            response_text = "Wait lang po, pa-review ko muna kay manager yung image. May iba ka pa bang kailangan? 😊"
                            Chat.objects.create(user=user_profile, message=message_text, reply=response_text)
                            send_message(sender_id, response_text, facebook_page_instance)
                            # Fetch all admins for the page
                            admin_users = UserProfile.objects.filter(page_id=user_profile.page_id, user_type='admin')
                            # Loop through all admins and send them a message
                            message_admin = f"{user_profile.name} sent an image 📷. Could this be a payment or confirmation? Just a note: I can't automate this. Thank you! 😊"
                            for admin in admin_users:
                                Chat.objects.create(user=admin, message='', reply=message_admin)
                                send_image(admin.facebook_id, image_url, facebook_page_instance)
                                send_message(
                                    admin.facebook_id,
                                    message_admin,
                                    facebook_page_instance
                                )
                elif message_text:
                    # Identify the user's task based on the message
                    identified_task = identify_task(message_text)
                    if identified_task:
                        if user_profile.task !=identified_task:
                            summarizer(user_profile)
                        user_profile.task = identified_task
                        user_profile.save()

                    # Save the incoming message to the Chat model
                    chat = Chat.objects.create(user=user_profile, message=message_text, reply='')

                    # Process the AI response based on the user's profile and task
                    response_text = ai_process(user_profile, facebook_page_instance, True)
                    
                    # Display topic on chat?
                    # if response_text and user_profile.user_type == 'admin':
                    #     response_text = f"{response_text}\n\n-Topic: {user_profile.task}"

                    # Send the AI-generated response back to the user
                    send_message(sender_id, response_text, facebook_page_instance)

                    # Save the reply to the Chat model
                    chat.reply = response_text
                    chat.save()
        return JsonResponse({'status': 'message processed', 'reply': response_text}, status=200)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def ai_process(user_profile, facebook_page_instance, first_run):
    # Retrieve the last 12 chat history for this user
    chat_history = Chat.objects.filter(user=user_profile, is_summarized=False).order_by('-timestamp')
    chat_history = list(chat_history)[::-1]  # Reverse to maintain correct chronological order
    if len(chat_history) > 6:
        # Trigger the summarizer function if there are more than 6 chats
        summarizer(user_profile)

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
        # Escalete before anything else
        activeHelp =  escalate.isThereQuestion(facebook_page_instance)
        if activeHelp:
            return escalate.bypass(activeHelp, chat_history, user_profile, facebook_page_instance)

        if not instruction(facebook_page_instance):
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
            elif user_profile.task == "sales":
                instruction = pos.instruction
                tools = pos.generate_tools()
                tool_function = pos.tool_function
            elif user_profile.task == "analyze":
                instruction = analyze.instruction
                tools = analyze.generate_tools()
                tool_function = analyze.tool_function
    if user_profile.user_type == 'customer':
        if user_profile.task == "customer":
            instruction = customer.instruction
            tools = customer.generate_tools()
            tool_function = customer.tool_function

    # Build AI message with instruction based on task
    if user_profile.user_type == "admin":
        current_task = user_profile.task.lower()  # Current task from user_profile
        business_instruction = instruction(facebook_page_instance)  # Get business-related info based on current task
        
        # Fetch the possible topics dynamically
        possible_topics = get_possible_topics()  # Assuming this function returns a list of possible topics
        
        # Prepare the system message dynamically with the current task and topic-specific instructions
        messages = [
            {
                "role": "system",
                "content": (
                    f"Your name is KENSHI short for (Kiosk and Easy Navigation System for Handling Inventory). "
                    f"Speak in taglish, keep replies short, No markdown just emoji and proper spacing, and focus STRICTLY on the current topic: '{current_task}'. "
                    f"Full Details of current topic: ({business_instruction}) "
                    f"Do not discuss anything unrelated unless the user shifts to a different task/topic"
                    f"In such cases, use the function 'change_topic' to automatically switch the topic to the relevant task "
                    f"The following topics are available: {', '.join(possible_topics)}. "
                    f"If the user mentions anything outside the listed topics, politely remind them to choose one from the available topics. "
                    # List topic informations.
                    f"{topic_description()}"
                )
            }
        ]

    if user_profile.user_type == "customer":
        messages = [
            {
                "role": "system",
                "content": (
                    "Your name is KENSHI short for 'Kiosk and Easy Navigation System for Handling Inventory'. "
                    "Speak in taglish, keep replies short, No markdown just emoji and proper spacing. "
                    "Your purpose is to assist customers with inquiries about products, promotions, pricing, inventory, and other business-related topics. "
                    "STRICTLY base your answers ONLY on the 'Information' and 'Additional Info' provided. "
                    "NEVER guess, assume, or invent answers. "
                    "If a customer asks a question unrelated to the business, politely redirect them to focus on business-related topics only. "
                    "If a customer asks a business-related question and the answer is not found in the 'Information' and 'Additional Info', unclear or incomplete, IMMEDIATELY trigger the 'ask_manager_help' function to ask the admin/owner/manager for clarification. "
                    "In case you need to apologize consider using the function 'ask_manager_help' first. "
                    "Under NO circumstances should you assume, invent, or provide information that is not explicitly found in the 'Information' and 'Additional Info'.\n\n"
                    + instruction(facebook_page_instance)
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

    # Add tool for changing topic if user is admin or user is not customer
    if user_profile.user_type == 'admin':
        tools = tools or []  # Ensure tools is initialized if None
        tools.append(change_topic.generate_tools())
    
    # Add tool for customer when the system does not know what to say
    if user_profile.user_type != 'admin':
        tools = tools or []  # Ensure tools is initialized if None
        tools.append(help.generate_tools())
        #print("###HELLO###", tools)

    # Attempt to generate a completion using the OpenAI API
    try:
        #print("AI CALL", messages)
        #print("AI Tools", tools)

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            tools=tools
        )
        response_content = completion.choices[0].message.content

        # Handle tool calls if present
        tool_calls = completion.choices[0].message.tool_calls
        print("tool_calls", tool_calls)
        if tool_calls:
            if any(tool_call.function.name == "change_topic" for tool_call in tool_calls):
                response_content = change_topic.tool_function(tool_calls, user_profile, facebook_page_instance)
            if any(tool_call.function.name == "ask_manager_help" for tool_call in tool_calls):
                response_content = help.tool_function(tool_calls, user_profile)
            else:
                response_content = tool_function(tool_calls, user_profile, facebook_page_instance)

            if not response_content and first_run:
                # Retry the process if tool function fails during the first run
                response_content = ai_process(user_profile, facebook_page_instance, False)
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

    return response_content

def chat_test_page(request):
    return render(request, 'chat_test.html')


def function_tester(request):
    # Call the inventory setup function
    inventory_setup.format_sheets("1u-Vy9b3KD4l3Ne2ZM3DXg8NmPxzv_QHJzXtzVPKeHu8")
    
    # Return a simple HTTP response to confirm it worked
    return HttpResponse("Inventory setup function executed successfully.")
