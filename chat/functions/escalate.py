import json
from chat.models import Help, UserProfile, Chat
from chat.utils import send_message
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()


def instruction(facebook_page_instance):
    # facebook_page_instance has attribute page_id
    # Retrieve the latest Help entry for the given page_id
    latest_help = Help.objects.filter(page_id=facebook_page_instance.page_id, answer__isnull=True).order_by('-id').first()

    # Check if there's a Help entry, and return the question if found
    if latest_help:
        question = latest_help.question
        return f"Getting the answer from the user (which is the owner) to the customer's question. Do not take any other actions or provide unrelated information. The customers question is: '{question}' Do not ask anything else."
    else:
        return None


def generate_tools():
    tools = []

    tools.append({
        "type": "function",
        "function": {
            "name": "answer",
            "description": "give answer the to escalated question from the customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "answer for the customer question."
                    },
                    "final_answer": {
                        "type": "boolean",
                        "description": "user is sure with the answer they give",
                    },
                },
                "required": ["answer", "final_answer"],
            },
        }
    })

    return tools

def tool_function(tool_calls, user_profile, facebook_page_instance):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        if function_name == "answer":
            answer = arguments_dict.get('answer')
            final_answer = arguments_dict.get('final_answer')
            if final_answer:
                latest_help = Help.objects.filter(page_id=facebook_page_instance.page_id, answer__isnull=True).order_by('-id').first()
                latest_help.answer = answer
                latest_help.save()

                # Message to notify admins
                message_admin = f"✅ Question: '{latest_help.question}' has been successfully answered! 🎉\n 📝 Answer: '{answer}'"
                
                # Fetch all admins for the page
                admin_users = UserProfile.objects.filter(page_id=user_profile.page_id, user_type='admin')

                # Loop through all admins and send them a message
                for admin in admin_users:
                    print("admin.facebook_id",admin.facebook_id)
                    print("user_profile.page_id",user_profile.facebook_id)
                    if str(admin.facebook_id).strip() != str(user_profile.facebook_id).strip():
                        # Save the incoming message to the Chat model
                        Chat.objects.create(user=admin, message='', reply=message_admin)
                        send_message(admin.facebook_id, message_admin, facebook_page_instance)

                # Send Message to user
                answer_to_customer = f"Here's what my manager says: {answer} 🤝🙂"
                userInstance = UserProfile.objects.get(facebook_id=latest_help.fb_id)
                Chat.objects.create(user=userInstance, message='', reply=answer_to_customer)
                send_message(latest_help.fb_id, answer_to_customer, facebook_page_instance)

                # Update additional info
                additional_info = facebook_page_instance.additional_info
                new_question = latest_help.question
                new_answer = answer

                # Prepare messages to summarize and update the additional information
                messages = [
                    {"role": "system", "content": "You are a summarizer. Combine the 'Current Information' with the New 'Q&A Data'. no markdown just sentence."},
                    {"role": "user", "content": f"Current Information: '{additional_info}'"},
                    {"role": "user", "content": f"Q&A Data: Customer Question: '{new_question}'. \nAnswer: '{new_answer}'"},
                ]

                try:
                    # Request a completion from the model
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                    )
                    facebook_page_instance.additional_info = completion.choices[0].message.content
                    facebook_page_instance.save()
                except Exception as e:
                    print(f"Error: {e}")

                return "✅ Thank you for giving an answer 🙏"
            else:
                return "So what should we tell the user?"
    return None
