import requests
from openai import OpenAI
from dotenv import load_dotenv
from enum import Enum
from googleapiclient.discovery import build
from google.oauth2 import service_account

from chat.models import Chat, UserProfile

load_dotenv()

client = OpenAI()

# START TOPIC ZONE
class Topics(Enum):
    INVENTORY = "inventory"
    SALES = "sales"
    ANALYZE =  "analyze"
    ATTENDANCE = "attendance"
    REPORTS = "reports"

def get_possible_topics():
    return [topic.value for topic in Topics]

def topic_description():
    return (
        "Guide on the function 'change_topic':\n"
        "- inventory: View, add, edit, or delete product/item records. This is for managing the items available for sale.\n"
        "- sales: Log new sales orders as the business owner when customers make purchases.\n"
        "- analyze: Review and obtain insights from sales history and data. Use this for generating reports based on past sales activities.\n"
        "- attendance and reports are not available currently."
    )

# END TOPIC ZONE

def get_service():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def send_message(recipient_id, message_text, facebook_page_instance):
    if facebook_page_instance.token == "antoken":
        print("recipient_id", recipient_id)
        print("message_text", message_text)
        print("facebook_page_instance", facebook_page_instance)
        return None
    post_url = f"https://graph.facebook.com/v11.0/me/messages?access_token={facebook_page_instance.token}"
    response_message = {
        'recipient': {'id': recipient_id},
        'message': {'text': message_text}
    }
    response = requests.post(post_url, json=response_message)
    return response.status_code

def send_image(recipient_id, image_url, facebook_page_instance):
    post_url = f"https://graph.facebook.com/v11.0/me/messages?access_token={facebook_page_instance.token}"
    message_data = {
        'recipient': {'id': recipient_id},
        'message': {
            'attachment': {
                'type': 'image',
                'payload': {'url': image_url}
            }
        }
    }

    response = requests.post(post_url, json=message_data)
    return response.status_code

def summarizer(user_profile):
    try:
        # Fetch all unsummarized chats for the user
        unsummarized_chats = Chat.objects.filter(user=user_profile, is_summarized=False)
        if not unsummarized_chats.exists():
            print(f"No unsummarized chats found for user with Facebook ID: {user_profile.name}")
            return None

        # Combine unsummarized chat messages
        chat_data = "\n".join([f"User: {chat.message}\nSystem: {chat.reply}" for chat in unsummarized_chats])

        # Combine with existing summary if available
        existing_summary = user_profile.summary or ""

        # Format messages array for summarization
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant summarizer. Your task is to combine new chat data with an existing summary, focusing solely on retaining important user information unrelated to business transactions. "
                    "Exclude all business-related data, such as sales, inventory, transactions, additions, updates, or deletions, as these are tracked separately in Google Sheets. "
                    "Preserve only personal user details and interactions, removing any business information to ensure the summary is concise. "
                    "Ensure the capture of all critical non-business related user information."
                )
            },
            {"role": "user", "content": f"Existing Summary: {existing_summary}"},
            {"role": "user", "content": f"New Chat Data: {chat_data}"},
        ]

        # Request a completion from the model
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
        )

        # Extract the summarized text
        summarized_text = completion.choices[0].message.content

        # Update the UserProfile summary
        user_profile.summary = summarized_text
        user_profile.save()

        # Mark all processed chats as summarized
        unsummarized_chats.update(is_summarized=True)

        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def summarize_sales(facebook_page_instance):
    if facebook_page_instance and getattr(facebook_page_instance, 'sheet_id', None):
        sheet_id = facebook_page_instance.sheet_id

        try:
            # Initialize the Sheets API service
            service = get_service()

            # Read the data from the "Sales" sheet
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range="Sales"
            ).execute()

            sales_message = ""
            values = result.get('values', [])
            if not values:
                sales_message = "No data found in the 'Sales' sheet."
            else:
                # Determine how many rows to fetch
                total_rows = len(values)
                start_row = max(0, total_rows - 400)  # Get the last 400 rows or all if less than 400

                # Include the header
                sales_data = values[:1] + values[start_row:]
                
                # Format the sheet data into a readable string
                sales_message = "Live Sales Data in Sheets Format:\n"
                for i, row in enumerate(sales_data):
                    row_info = f"Row {i + 1}: {', '.join(row)}"
                    sales_message += row_info + "\n"
        
            # Format messages array for summarization
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You summarize and analize data. Here is the data to analize"
                    ),
                },
                {"role": "user", "content": f"Summary of recent sales from google sheets: {sales_message}"},
            ]
            
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0,
            )

            summarized_text = completion.choices[0].message.content
            facebook_page_instance.sales = summarized_text
                    
        except Exception as e:
            sales_message = f"An error occurred: {str(e)}"
    return None
        