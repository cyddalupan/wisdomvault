import json
from chat.cache import delete_cache
from chat.functions.customer import get_business_info
from chat.models import Help, UserProfile, Chat
from chat.service import get_service
from chat.utils import send_message, summarizer
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

def isThereQuestion(facebook_page_instance):
    # Check if there is a pending help request
    pending_help = Help.objects.filter(page_id=facebook_page_instance.page_id, answer__isnull=True).order_by('-id').first()
    return pending_help


def bypass(activeHelp, chat_history, user_profile, facebook_page_instance):
    question = activeHelp.question
    messages = [
        {
            "role": "system",
            "content": (
                f"Your name is KENSHI. You are designed to assist by gathering answers from the user (owner) to customer inquiries and nothing else."
                f"STRICTLY focus only on asking the user to answer the customer's question."
                f"If the user mentions anything besides answering the question, politely remind them to answer the question from the user first. "
                f"Do not provide any unrelated information, explanations, or assumptions. Do not take any other actions just ask the answer to the question."
                f"The customer's question is: '{question}'."
                f"Simply ask the user to provide an answer to this question."
                "then trigger the answer function when you get the answer."
            )
        }
    ]

    # Include previous chat history in the conversation
    for chat in chat_history:
        if chat.message and chat.message != "":
            messages.append({"role": "user", "content": chat.message})
        if chat.reply and chat.reply != "":
            messages.append({"role": "assistant", "content": chat.reply})
    
    tools = generate_tools()

    completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            tools=tools
        )
    response_content = completion.choices[0].message.content
    tool_calls = completion.choices[0].message.tool_calls
    print("escalate tool_calls", tool_calls)
    if tool_calls:
        response_content = tool_function(tool_calls, user_profile, facebook_page_instance)
    print("emergency result", response_content)
    return response_content

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

def save_additional_info(facebook_page_instance, additional_info):
    cache_type = "business_info"
    service = get_service()
    
    try:
        # Update the value in cell B3 of the "Settings" sheet
        service.spreadsheets().values().update(
            spreadsheetId=facebook_page_instance.sheet_id,
            range="Settings!B3",
            valueInputOption="USER_ENTERED",
            body={"values": [[additional_info]]}
        ).execute()
        delete_cache(facebook_page_instance.page_id, cache_type)
        return True
    except Exception as e:
        return False

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
                info, additional_info = get_business_info(facebook_page_instance)
                additional_info = additional_info
                last_question = latest_help.question
                last_answer = answer

                # Prepare messages to summarize and update the additional information
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a summarizer. Your task is to combine 'Current Information' with the latest 'Owner Q&A Data'. "
                            "Ensure the summary retains all important details and context from the current information and the new Q&A. "
                            "Remove redundant or unimportant details while keeping the summary concise and clear. "
                            "No markdown, just sentences."
                        ),
                    },
                    {"role": "user", "content": f"Current Information: '{additional_info}'"},
                    {
                        "role": "user",
                        "content": (
                            f"Owner Q&A Data: "
                            f"Customers's Last Question: '{last_question}'. "
                            f"Owner's Answer: '{last_answer}'."
                        ),
                    },
                ]

                try:
                    # Request a completion from the model
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        temperature=0,
                    )
                    save_additional_info(facebook_page_instance, completion.choices[0].message.content)
                    facebook_page_instance.save()
                except Exception as e:
                    print(f"Error: {e}")
                
                summarizer(user_profile)

                return "✅ Thank you for giving an answer 🙏"
            else:
                return "So what should we tell the user?"
    return None
