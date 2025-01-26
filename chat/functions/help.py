import json
from chat.utils import send_message, summarizer
from chat.models import Help, UserProfile, Chat
from page.models import FacebookPage

def generate_tools():
    return {
        "type": "function",
        "function": {
            "name": "ask_manager_help",
            "description": "if the system does not know what to say, use this to ask admin what to say",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A structured question based on what user is saying and asking"
                    }
                },
                "required": ["question"]
            }
        }
    }

def tool_function(tool_calls, user_profile):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        print("### Function", function_name)
        if function_name == "ask_manager_help":
            question = arguments_dict.get('question')
            print("### Function question", question)

            # Save the question into the Help model
            help_entry = Help.objects.create(
                page_id=user_profile.page_id,
                fb_id=user_profile.facebook_id,
                name=user_profile.name,
                question=question,
                answer=None  # Leave blank initially; answer can be filled later
            )

            # Message to notify admins
            message_admin = f"❓ User {user_profile.name} asked: '{question}'\n💬 What should I say? 🤔"
            facebook_page_instance = FacebookPage.objects.get(page_id=user_profile.page_id)

            # Fetch all admins for the page
            admin_users = UserProfile.objects.filter(page_id=user_profile.page_id, user_type='admin')

            # Loop through all admins and send them a message
            for admin in admin_users:
                # Save the incoming message to the Chat model
                Chat.objects.create(user=admin, message='', reply=message_admin)
                send_message(admin.facebook_id, message_admin, facebook_page_instance)
            
            summarizer(user_profile)

            return "⏳ Let me check with my manager. Wait lang po 🙏"
    return None
