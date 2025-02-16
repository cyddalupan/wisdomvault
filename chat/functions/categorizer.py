import json
from openai import OpenAI
from dotenv import load_dotenv
from enum import Enum

from chat.utils import summarize_sales, summarizer

load_dotenv()

client = OpenAI()

class Topics(Enum):
    INVENTORY = "inventory"
    SALES = "sales"
    ANALYZE = "analyze"
    SCHEDULE = "schedule"
    # ATTENDANCE = "attendance"
    # REPORTS = "reports"
    OTHER = "other"

def get_possible_topics(facebook_page):
    topics = []
    
    if facebook_page.is_inventory:
        topics.append(Topics.INVENTORY.value)
    
    if facebook_page.is_pos:
        topics.append(Topics.SALES.value)
        topics.append(Topics.ANALYZE.value)
    
    if facebook_page.is_schedule:
        topics.append(Topics.SCHEDULE.value)
    
    topics.append(Topics.OTHER.value)
    
    return topics

def topic_description(facebook_page):
    description = "Guide on the function 'get_category':\n"
    
    if facebook_page.is_inventory:
        description += "- inventory: View, add, edit, or delete product/item records. This is for managing the items available for sale.\n"
    
    if facebook_page.is_pos:
        description += "- sales: Log new sales orders as the business owner when customers make purchases. Do not switch here if the user wants to check sales status; that is for analyze.\n"
        description += "- analyze: Review and obtain insights from sales history and data. Use this for generating reports based on past sales activities. Trigger here is something like: what is the sales status for today, this week, etc.\n"
    
    if facebook_page.is_schedule:
        description += "- schedule: View the latest schedules and availability for bookings. For any schedule-related questions, use this option. \n"
    
    # Add Instruction for Others
    description += "- other: when you dont know the topic use 'other' as topic.\n"

    return description

def getCategory(user_profile, chat_history, facebook_page):
    # Get the possible topics and their descriptions
    possible_topics = get_possible_topics(facebook_page)
    topic_descriptions = topic_description(facebook_page)
    
    # Create a simple string of options
    options_list = "\n".join(f"- {topic}" for topic in possible_topics)

    # System message that instructs the LLM
    system_message = (
        "You are a categorizer. Your task is to identify and classify the user's conversation into one of the "
        "available categories and trigger the 'get_category' tool function. sense sudden tone change. Always categorize the message into "
        "one of the following options or use category 'other' if it doesn't fit any category:\n"
        f"{options_list}\n"
        "Descriptions:\n"
        f"{topic_descriptions}"
    )

    # Prepare the messages for the LLM
    messages = [
        {
            "role": "system",
            "content": system_message
        }
    ]
    
    for chat in chat_history:
        if chat.message and chat.message.strip():
            messages.append({"role": "user", "content": chat.message})
        if chat.reply and chat.reply.strip():
            messages.append({"role": "assistant", "content": chat.reply})

    tools = [{
        "type": "function",
        "function": {
            "name": "get_category",
            "description": (
                "This function runs 100%. Pick what category the user is talking about"
                f"The following categories available: {options_list}. "
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": possible_topics,
                        "description": "The Category the user is refering to."
                    }
                },
                "required": ["category"]
            }
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

    tool_calls = completion.choices[0].message.tool_calls or []
    print("category tool_calls", tool_calls)
    for tool_call in tool_calls:
        if tool_call.function.name == "get_category":
            arguments = tool_call.function.arguments
            arguments_dict = json.loads(arguments)
            category = arguments_dict.get('category')
            if user_profile.task != category:
                if category == Topics.ANALYZE.value:
                    summarize_sales(facebook_page)
                summarizer(user_profile)
                user_profile.task = category
                user_profile.save()
    return user_profile.task