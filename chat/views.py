
import os
import json
import traceback
import requests
from openai import OpenAI
from django.http import JsonResponse, HttpResponse

from page.models import FacebookPage
from .models import Chat, UserProfile
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
        # Verification for the webhook setup with Facebook
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
                message_text = event['message'].get('text')  # Message from the user

                # Check if the message_text is not None or empty
                if message_text:
                    # Handle user profile creation or retrieval
                    user_profile, created = UserProfile.objects.get_or_create(
                        facebook_id=sender_id,
                        defaults={
                            'facebook_id': sender_id,
                            'page_id': page_id,
                            'full_name': 'Facebook User'  # Default value if not fetched yet
                        }
                    )

                    # Save the incoming message to the Chat model
                    chat = Chat.objects.create(user=user_profile, message=message_text, reply='')

                    page_id = user_profile.page_id
                    # Fetch the FacebookPage instance from the database
                    facebook_page_instance = FacebookPage.objects.get(page_id=page_id)

                    # AI Logic to process the message and generate a reply
                    response_text = ai_process(user_profile, facebook_page_instance)

                    # Send a reply back to the user
                    send_message(sender_id, response_text, facebook_page_instance)

                    # Save the reply in the database
                    chat.reply = response_text
                    chat.save()

        return JsonResponse({'status': 'message processed', 'reply': response_text}, status=200)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

def send_message(recipient_id, message_text, facebook_page_instance):
    """
    Sends a message back to the Facebook user using Facebook's Send API.
    """
    post_url = f"https://graph.facebook.com/v11.0/me/messages?access_token={facebook_page_instance.token}"
    response_message = {
        'recipient': {'id': recipient_id},
        'message': {'text': message_text}
    }

    response = requests.post(post_url, json=response_message)
    return response.status_code

def ai_process(user_profile, facebook_page_instance):
    # Retrieve the last 20 chat history for this user
    chat_history = Chat.objects.filter(user=user_profile).order_by('-timestamp')[:20]
    chat_history = list(chat_history)[::-1]  # Reverse to maintain correct chronological order

    product_info_template = (
        "You are a friendly and persuasive chatbot representing '{agency_name},' a trusted overseas employment agency. "
        "Since {establishment_date}, we have been successfully deploying workers to {deployment_countries} and many other "
        "destinations. We are located in '{agency_location}'. Your goal is to "
        "highlight our company's stability, extensive experience, and the amazing opportunities available for applicants. "
        "Convince potential applicants that '{agency_name}' is their best option for securing a well-paying, stable job in "
        "these countries. {cash_assistance_statement}."
        "If unsure about information, assure the user we will call them with the accurate details."
    )

    # Extract agency details from the instance
    agency_details = {
        "agency_name": facebook_page_instance.agency_name,
        "establishment_date": facebook_page_instance.establishment_date,
        "deployment_countries": facebook_page_instance.deployment_countries,
        "agency_location": facebook_page_instance.agency_location,
        "cash_assistance_statement": facebook_page_instance.cash_assistance_statement
    }
    
    product_info = product_info_template.format(**agency_details)

    ask_message = ""
    # Ask for User info
    if not user_profile.full_name or user_profile.full_name == "Facebook User":
        ask_message = "Ask for the user's real full name because the Facebook name might not be accurate."
    if not user_profile.contact_number:
        ask_message += " Ask for the user's contact number."

    # Check if full name and contact number are provided, then ask for additional info
    if user_profile.full_name and user_profile.contact_number:
        if not user_profile.age:
            ask_message += " Ask for the user's age."
        if not user_profile.whatsapp_number:
            ask_message += " Ask for the user's WhatsApp number."
        if not user_profile.location:
            ask_message += " Ask for the user's location or address."

    if ask_message != '':
        function_pusher = "If the user's profile information (e.g., full name, contact number, and other details) is incomplete or missing, use the available tools to request and save this information."
    else:
        function_pusher = "All the user information is complete so tell the user that we will call him or her for more information."

    messages = [
        {"role": "system", "content": "Talk in taglish. Use common words only. dont exceed 200 characters. ask question one at a time" + function_pusher},
        {"role": "system", "content": f"Product Info: {product_info}"} 
    ]

    if ask_message != '':
        messages.append({"role": "system", "content": ask_message})

    # Include previous chat history in the conversation
    for chat in chat_history:
        messages.append({"role": "user", "content": chat.message})
        if chat.reply != "":
            messages.append({"role": "system", "content": chat.reply})

    tools = generate_tools(user_profile)

    response_content = ""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )
        response_content = completion.choices[0].message.content

        tool_calls = completion.choices[0].message.tool_calls
        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = tool_call.function.arguments
                arguments_dict = json.loads(arguments)

                # Validation before saving data
                if function_name == "save_name":
                    full_name = arguments_dict.get('full_name', '')
                    if isinstance(full_name, str) and len(full_name) <= 255:
                        user_profile.full_name = full_name
                elif function_name == "save_age":
                    age = arguments_dict.get('age', '')
                    if isinstance(age, str) and len(age) <= 30:
                        user_profile.age = age
                elif function_name == "save_contact_number":
                    contact_number = arguments_dict.get('contact_number', '')
                    if isinstance(contact_number, str) and len(contact_number) <= 20:
                        user_profile.contact_number = contact_number
                elif function_name == "save_whatsapp_number":
                    whatsapp_number = arguments_dict.get('whatsapp_number', '')
                    if isinstance(whatsapp_number, str) and len(whatsapp_number) <= 20:
                        user_profile.whatsapp_number = whatsapp_number
                elif function_name == "save_location":
                    location = arguments_dict.get('location', '')
                    if isinstance(location, str) and len(location) <= 255:
                        user_profile.location = location

            # Save updated user profile in Django without errors
            user_profile.is_copied = False
            user_profile.save()

            # Call without function or tools
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            response_content = completion.choices[0].message.content

    except Exception as e:
        traceback.print_exc()
        response_content = str(e)
    return response_content

def generate_tools(user_profile):
    tools = []

    # Special case for full_name
    if not user_profile.full_name or user_profile.full_name == "Facebook User":
        tools.append({
            "type": "function",
            "function": {
                "name": "save_name",
                "description": "save name of user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "full_name": {
                            "type": "string",
                            "description": "user full name",
                        },
                    },
                    "required": ["full_name"],
                },
            }
        })

    # Other fields
    fields = [
            {"field": "age", "function_name": "save_age", "description": "save age of user", "parameter_type": "string", "parameter_name": "age", "var_desc": "users age"},
            {"field": "contact_number", "function_name": "save_contact_number", "description": "save contact number of user. make sure this is a valid philippine number", "parameter_type": "string", "parameter_name": "contact_number", "var_desc": "users philippine contact number only"},
            {"field": "whatsapp_number", "function_name": "save_whatsapp_number", "description": "save whatsapp number of user", "parameter_type": "string", "parameter_name": "whatsapp_number", "var_desc": "users whatsapp number"},
            {"field": "location", "function_name": "save_location", "description": "save users valid complete philippine address", "parameter_type": "string", "parameter_name": "location", "var_desc": "users valid complete address in the philippines only"},
    ]

    for field_info in fields:
        if not getattr(user_profile, field_info["field"]):
            tools.append({
                "type": "function",
                "function": {
                    "name": field_info["function_name"],
                    "strict": True,
                    "description": field_info["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {
                            field_info["parameter_name"]: {
                                "type": field_info["parameter_type"],
                                "description": field_info["var_desc"],
                            },
                        },
                        "required": [field_info["parameter_name"]],
                        "additionalProperties": False,
                    },
                }
            })

    if len(tools) == 0:
        return None

    return tools

class FacebookPageInstance:
    def __init__(self, token):
        self.token = token

def chat_test_page(request):
    return render(request, 'chat_test.html')
