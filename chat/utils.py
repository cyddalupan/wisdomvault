import requests
from openai import OpenAI
from dotenv import load_dotenv
from enum import Enum

from chat.models import Chat, UserProfile

load_dotenv()

client = OpenAI()

class Topics(Enum):
    INVENTORY = "inventory"
    SALES = "sales"
    ATTENDANCE = "attendance"
    REPORTS = "reports"

def get_possible_topics():
    return [topic.value for topic in Topics]

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

def summarizer(user_profile):
    print("summarize function opened")
    try:
        # Fetch all unsummarized chats for the user
        unsummarized_chats = Chat.objects.filter(user=user_profile, is_summarized=False)
        print("unsummarized_chats", unsummarized_chats)
        if not unsummarized_chats.exists():
            print(f"No unsummarized chats found for user with Facebook ID: {user_profile.name}")
            return None

        # Combine unsummarized chat messages
        chat_data = "\n".join([f"User: {chat.message}\nSystem: {chat.reply}" for chat in unsummarized_chats])
        print("chat_data", chat_data)

        # Combine with existing summary if available
        existing_summary = user_profile.summary or ""
        print("existing_summary", existing_summary)

        # Format messages array for summarization
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant summarizer. Your task is to combine new chat data with an existing summary. "
                    "Make sure to retain all important details and context from both the existing summary and the new chat data. "
                    "Remove redundant or unimportant details while keeping the summary concise and relevant. "
                    "Ensure that critical information is not lost and prioritize clarity over brevity. No markdown, just sentences."
                ),
            },
            {"role": "user", "content": f"Existing Summary: {existing_summary}"},
            {"role": "user", "content": f"New Chat Data: {chat_data}"},
        ]

        print("messages",messages)

        # Request a completion from the model
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
        )

        # Extract the summarized text
        summarized_text = completion.choices[0].message.content
        print("summarized_text",summarized_text)

        # Update the UserProfile summary
        user_profile.summary = summarized_text
        user_profile.save()

        # Mark all processed chats as summarized
        unsummarized_chats.update(is_summarized=True)

        print("Summary updated successfully.")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
