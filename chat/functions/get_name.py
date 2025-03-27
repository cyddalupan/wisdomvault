import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

def bypass_get_name(chat_history, user_profile):
    messages = [
        {
            "role": "system",
            "content": (
                "Speak in taglish, keep replies short, No markdown just emoji and proper spacing. "
                f"Your name is KENSHI. your task for now is to get name of the user and nothing else."
                f"STRICTLY focus only on asking the name of the user because maybe the name in facebook is different. "
                f"If the user mentions anything besides giving name, politely remind them to give name first before you can do other things that can helps them. "
                "trigger save_name tool function to save the name. "
                "If the user chooses not to provide a name, kindly ask them again. If they still prefer to keep it private, proceed with trigger save_name tool function as 'no_name'. "
            )
        }
    ]

    # Include previous chat history in the conversation
    for chat in chat_history:
        if chat.message and chat.message != "":
            messages.append({"role": "user", "content": chat.message})
        if chat.reply and chat.reply != "":
            messages.append({"role": "assistant", "content": chat.reply})

    tools = [{
        "type": "function",
        "function": {
            "name": "save_name",
            "description": "save name of user",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "name of the user."
                    },
                },
                "required": ["name"],
            },
        }
    }]
    # print("CATEGORY MESSAGE:", messages)
    # print("CATEGORY TOOL", tools)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0,
        tools=tools
    )
    
    response_content = completion.choices[0].message.content
    tool_calls = completion.choices[0].message.tool_calls or []
    # print("get name tool_calls", tool_calls)
    for tool_call in tool_calls:
        if tool_call.function.name == "save_name":
            arguments = tool_call.function.arguments
            arguments_dict = json.loads(arguments)
            name = arguments_dict.get('name')
            user_profile.name = name
            user_profile.save()
    return response_content
