import requests
from openai import OpenAI
from dotenv import load_dotenv

from chat.models import Chat
from chat.service import get_service

load_dotenv()

client = OpenAI()

def getChatHistory(user_profile):
    # Retrieve the last 6 chat history for this user
    chat_history = Chat.objects.filter(user=user_profile, is_summarized=False).order_by('-timestamp')
    chat_history = list(chat_history)[::-1]  # Reverse to maintain correct chronological order
    if len(chat_history) > 6:
        # Trigger the summarizer function if there are more than 6 chats
        summarizer(user_profile)
    return chat_history

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
                    "Never save any item on summary included in inventory or not. "
                    "Preserve only personal user details and interactions, removing any business information to ensure the summary is concise. "
                    "Ensure the capture of all critical non-business related user information. "
                )
            },
            {"role": "user", "content": f"Existing Summary: {existing_summary}"},
            {"role": "user", "content": f"New Chat Data: {chat_data}"},
        ]

        # Request a completion from the model
        completion = client.chat.completions.create(
            model="gpt-4.1-nano",
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
                range="Orders"
            ).execute()

            sales_message = ""
            values = result.get('values', [])
            if not values:
                sales_message = "No data found in the 'Sales' sheet."
            else:
                # Determine how many rows to fetch
                total_rows = len(values)
                start_row = max(0, total_rows - 200)  # Get the last 400 rows or all if less than 400

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
                model="gpt-4.1-nano",
                messages=messages,
                temperature=0,
            )

            summarized_text = completion.choices[0].message.content
            facebook_page_instance.sales = summarized_text
                    
        except Exception as e:
            sales_message = f"An error occurred: {str(e)}"
    return None

def escalate_normal(legacy):
    tmp_legacy = legacy.copy()
    message = {
        "role": "system",
        "content": (
            "You check if the last assistant reply is ok. just reply 'GOOD' or 'BAD' "
            "If its ok just reply 'GOOD'"
            "reply 'BAD' If you think reply is bad, an apology or should have been a function call"
        ),
    }
    
    if tmp_legacy is None:
        tmp_legacy = []

    # Insert the new message at the start of the legacy list
    tmp_legacy.insert(0, message)

    # Escalate normal chat
    completion = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=tmp_legacy,
        temperature=0.1,
    )
    return completion.choices[0].message.content

def escalate_bad(legacy, tools):
    tmp_legacy = legacy.copy()

    message = {
        "role": "system",
        "content": (
            "You give a better response or maybe a function call should have been triggered because the system give a bad response. "
            "the bad response is the last system message and you should change that to a better one. "
            "consider everything before giving a better response make sure its correct."
        ),
    }
    
    if tmp_legacy is None:
        tmp_legacy = []

    # Insert the new message at the start of the legacy list
    tmp_legacy.insert(0, message)
    
    # Escalate normal chat
    completion = client.chat.completions.create(
        model="o4-mini",
        messages=tmp_legacy,
        tools=tools
    )
    return completion

def escalate_function(legacy, tools):
    tmp_legacy = legacy.copy()

    # Escalate normal chat
    completion = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=tmp_legacy,
        temperature=0.2,
        tools=tools
    )
    return completion

def escalate_master(legacy, tools, call1, call2):
    tmp_legacy = legacy.copy()

    message = {
    "role": "system",
        "content": (
            "Trigger the tool call function with complete accuracy and provide the correct function based on detailed analysis of two sets of parameters from GPT.  Note: Ensure accuracy by analyzing both parameter sets thoroughly before selecting the function call."
            f"GPT1 suggests: {call1} and GPT2 suggests: {call2}. "
            "Please carefully evaluate both suggestions and determine the appropriate parameters to use. "
            "The following messages are the instructions that GPT1 and GPT2 received, so decide wisely."
        ),
    }
    
    if tmp_legacy is None:
        tmp_legacy = []

    # Insert the new message at the start of the legacy list
    tmp_legacy.insert(0, message)

    # Escalate normal chat
    completion = client.chat.completions.create(
        model="o4-mini",
        messages=tmp_legacy,
        tools=tools
    )
    return completion


