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
    
    if facebook_page.is_scheduling:
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
    
    if facebook_page.is_scheduling:
        description += "- schedule: View the latest schedules and availability for bookings. For any schedule-related questions, use this option. \n"
    
    # Add Instruction for Others
    description += "- other: when you dont know the topic use 'other' as topic.\n"

    return description
