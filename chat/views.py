
import os
import json
import traceback
import requests
from openai import OpenAI
from django.http import JsonResponse, HttpResponse

from chat.functions import inventory, inventory_setup, verify_user
from page.models import FacebookPage
from .models import Chat, UserProfile
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from dotenv import load_dotenv

## TEST IMPORTS
import os
from django.http import JsonResponse
from django.shortcuts import render
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

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
                        }
                    )

                    # Save the incoming message to the Chat model
                    chat = Chat.objects.create(user=user_profile, message=message_text, reply='')

                    page_id = user_profile.page_id
                    # Fetch the FacebookPage instance from the database
                    facebook_page_instance = FacebookPage.objects.get(page_id=page_id)

                    # AI Logic to process the message and generate a reply
                    response_text = ai_process(user_profile, facebook_page_instance, True)

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

def ai_process(user_profile, facebook_page_instance, first_run):
    # Retrieve the last 12 chat history for this user
    chat_history = Chat.objects.filter(user=user_profile).order_by('-timestamp')[:12]
    chat_history = list(chat_history)[::-1]  # Reverse to maintain correct chronological order

    instruction = ""
    tools = None
    if user_profile.task == "verify_user":
        instruction = verify_user.instruction
        tools = verify_user.generate_tools()
        tool_function = verify_user.tool_function
    if user_profile.task == "inventory_setup":
        instruction = inventory_setup.instruction
        tools = inventory_setup.generate_tools()
        tool_function = inventory_setup.tool_function
    if user_profile.task == "inventory":
        instruction = inventory.instruction
        tools = inventory.generate_tools()
        tool_function = inventory.tool_function
    

    messages = [
        {"role": "system", "content": "Your name is KENSHI (Kiosk and Easy Navigation System for Handling Inventory). Talk in taglish. keep reply short. give instructions or ask questions one at a time"},
        {"role": "system", "content": f"Focus on: {instruction(facebook_page_instance)}"} 
    ]

    # Include previous chat history in the conversation
    for chat in chat_history:
        messages.append({"role": "user", "content": chat.message})
        if chat.reply and chat.reply != "":
            messages.append({"role": "system", "content": chat.reply})

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
            response_content = tool_function(tool_calls, user_profile, facebook_page_instance)

            if not response_content and first_run:
                response_content = ai_process(user_profile, facebook_page_instance, False)
            if not first_run:
                response_content = "I am sorry it seems like I am getting confused. can we start again?"

    except Exception as e:
        traceback.print_exc()
        response_content = str(e)
    return response_content

class FacebookPageInstance:
    def __init__(self, token):
        self.token = token

def chat_test_page(request):
    return render(request, 'chat_test.html')

# Define the scope and sample spreadsheet information
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SAMPLE_SPREADSHEET_ID = "1u-Vy9b3KD4l3Ne2ZM3DXg8NmPxzv_QHJzXtzVPKeHu8"
SAMPLE_RANGE_NAME = "'Sheet1'!A2:F3"

def quickstart(request):
    creds = service_account.Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
            .execute()
        )
        values = result.get("values", [])

        return JsonResponse({"data": values})

    except HttpError as err:
        return JsonResponse({"error": str(err)})
    
def add_edit_data(request):
    creds = service_account.Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    try:
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        
        # Data to be added or updated
        values = [
            ["Name", "Age", "Location"],
            ["Alice", 30, "New York"],
            ["Bob", 25, "San Francisco"]
        ]
        body = {"values": values}

        # Update or append data in a specific range
        result = sheet.values().update(
            spreadsheetId=SAMPLE_SPREADSHEET_ID,
            range="'Sheet1'!A1:C3",
            valueInputOption="RAW",
            body=body
        ).execute()

        return JsonResponse({"updatedCells": result.get("updatedCells")})

    except HttpError as err:
        return JsonResponse({"error": str(err)})