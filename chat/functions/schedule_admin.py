import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import time
from datetime import datetime

from chat.service import get_service
from chat.utils import summarize_sales, summarizer

def instruction(facebook_page_instance): 
    latest_schedules = latest_data(facebook_page_instance)  # Get the latest schedule data

    if "No data found" in latest_schedules:
        return "No schedule data available at this time."

    # Prepare the instruction for the LLM
    summary = "For admin reference Here are the latest schedule data:\n"
    
    for line in latest_schedules.splitlines()[1:]:  # Skip the header
        if "N/A" in line:
            summary += f"Available: {line}\n"  # No bookings (Name: N/A)
        else:
            summary += f"Booked: {line}\n"  # Has bookings (Name and FB_ID present)

    return summary + "\nNote that if user wants to customize the schedules tell admin to change on the spread sheets"

def latest_data(facebook_page_instance):
    print("Fetching latest bookings from Google Sheets...")
    if facebook_page_instance and getattr(facebook_page_instance, 'sheet_id', None):
        sheet_id = facebook_page_instance.sheet_id

        try:
            # Initialize the Sheets API service
            service = get_service()

            # Read the data from the "Bookings" sheet
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range="Bookings"
            ).execute()

            values = result.get('values', [])
            if not values:
                return "No data found in the 'Bookings' sheet."

            available_message = "Latest Bookings Data:\n"
            # Slice values to exclude headers, starting from row 6
            latest_data = values[6:]  # All rows excluding headers

            # Limit to the latest 100 entries
            latest_data = latest_data[-20:]

            for i, row in enumerate(latest_data, start=7):  # Start from 7 to match row number in output
                available_message += f"Row {i}: {row[2]}, {row[3]} (FB_ID: {row[4] if len(row) > 4 else 'N/A'}, Name: {row[5] if len(row) > 5 else 'N/A'})\n"

            return available_message if latest_data else "No available data found."

        except Exception as e:
            return f"Error fetching latest bookings: {e}"
