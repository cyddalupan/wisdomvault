import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import time
import datetime

from chat.utils import get_service, summarize_sales, summarizer

# Global variable to store the fetched data and its timestamp
cached_data = {
    'data': None,
    'timestamp': 0
}

def instruction(facebook_page_instance, target_row=None):
    sales_summary = facebook_page_instance.sales

    return (
        f"Analize Data: User wants information about recent sales."
        f"Summary of recent transactions: {sales_summary}"
    )

def generate_tools():
    return None


def tool_function(tool_calls, user_profile, facebook_page_instance):
    return None
