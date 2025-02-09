import time
import json
from datetime import datetime

from chat.utils import get_service

# Global variable for caching
cached_data = {
    'data': None,
    'timestamp': 0
}

cached_available_data = {
    'data': None,
    'timestamp': 0
}

def read_bookings(facebook_page_instance):
    global cached_data  # Use the global variable

    # Check if the cached data is older than 20 seconds
    current_time = time.time()
    if current_time - cached_data['timestamp'] > 20:
        print("Fetching new data from Google Sheets...")
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
                    bookings_message = "No data found in the 'Bookings' sheet."
                else:
                    # Format the sheet data into a readable string
                    bookings_message = "Live Bookings Data in Sheets Format:\n"
                    for i, row in enumerate(values):
                        row_info = f"Row {i + 1}: {', '.join(row)}"
                        bookings_message += row_info + "\n"

                # Cache the data and timestamp
                cached_data['data'] = bookings_message
                cached_data['timestamp'] = current_time

            except Exception as e:
                return f"Error fetching bookings data: {e}"

    return cached_data['data']

def available_schedule(facebook_page_instance):
    global cached_available_data  # Use the global variable

    # Check if the cached data is older than 20 seconds
    current_time = time.time()
    if current_time - cached_available_data['timestamp'] > 20:
        print("Fetching available schedules from Google Sheets...")
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
                    available_message = "No data found in the 'Bookings' sheet."
                else:
                    available_message = "Available Dates from Bookings Data:\n"
                    current_date = datetime.now()

                    for i, row in enumerate(values[2:], start=2):  # Assuming the first two rows are headers
                        # Check if the second column (date) exists and is not empty
                        date_str = row[2] if len(row) > 2 else None
                        name = row[5] if len(row) > 5 else None

                        if date_str and name is None:  # Only proceed if there's a date and no name
                            date = datetime.strptime(date_str, '%Y-%m-%d')
                            if date > current_date:
                                available_message += f"Row {i + 1}: {date_str}, {row[3]} (FB_ID: {row[4] if len(row) > 4 else 'N/A'})\n"

                # Cache the data and timestamp
                cached_available_data['data'] = available_message
                cached_available_data['timestamp'] = current_time

            except Exception as e:
                return f"Error fetching available schedules: {e}"

    return cached_available_data['data']

# Fix Save Booking
def save_booking(facebook_page_instance, row, fb_id, name, mobile, remarks=None):
    if facebook_page_instance and getattr(facebook_page_instance, 'sheet_id', None):
        sheet_id = facebook_page_instance.sheet_id

        try:
            # Initialize the Sheets API service
            service = get_service()

            # Subtract 1 for 0-indexing in API
            row_index = row

            # Read the current row data to preserve any existing values
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f"Bookings!A{row_index + 1}:H{row_index + 1}"
            ).execute()

            # Retrieve the current row, or default to an empty list if not found
            current_row = result.get('values', [[]])[0]

            # Prepare the new row data
            updated_values = [
                current_row[0],  # Keep existing value in column A
                current_row[1],  # Keep existing value in column B
                current_row[2],  # Keep existing value in column C (Date)
                current_row[3],  # Keep existing value in column D (Time)
                fb_id if fb_id else current_row[4],  # Update FB_ID if provided
                name if name else current_row[5],  # Update Name if provided
                mobile if mobile else current_row[6],  # Update Mobile if provided
                remarks if remarks is not None else current_row[7]  # Update Remarks if provided
            ]

            # Prepare the request body for the update
            body = {
                'values': [updated_values]
            }

            # Update the row in the spreadsheet
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"Bookings!A{row_index + 1}:H{row_index + 1}",
                valueInputOption="USER_ENTERED",  # Allow for user-entered values and formatting
                body=body
            ).execute()

            return f"Booking updated for row {row + 1}: {name}"

        except Exception as e:
            return f"Error saving booking: {e}"
    else:
        return "Facebook page instance or sheet_id is missing."

def instruction(facebook_page_instance):
    schedules = available_schedule(facebook_page_instance)
    current_datetime = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    return (f"\nIMPORTANT: If no relevant topic is being discussed or if you don't know what to say, proactively suggest booking a schedule. "
            f"Do not walk in without a schedule; please book a schedule first. "
            f"We only book schedules that are in the available schedules. If there are no available schedules, inform the user that there are none at the moment and suggest checking other times. "
            f"Make sure to check today's date and time: {current_datetime}. "
            f"Only Recommend an available schedule from the list gathered earlier (sheet row) to the user. "
            f"Gather the date, time (sheet row), mobile number, and optional remarks. "
            f"Use the book_schedule tool call function when booking a schedule with us. "
            f"\n\nAvailable schedules from Google Sheets:\n{schedules}")

def generate_tools():
    return {
        "type": "function",
        "function": {
            "name": "book_schedule",
            "description": "user books a schedule with us.",
            "parameters": {
                "type": "object",
                "properties": {
                    "row_number": {
                        "type": "integer",
                        "description": "row number of the schedule selected",
                    },
                    "mobile": {
                        "type": "string",
                        "description": "user's mobile number",
                    },
                    "remarks": {
                        "type": "string",
                        "description": "optional user's remarks or additional info for the schedule",
                    },
                },
                "required": ["row_number", "mobile"],
            },
        }
    }

def book_schedule(tool_calls, user_profile, facebook_page_instance):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)
        fb_id = user_profile.facebook_id
        name = user_profile.name
        row_number = arguments_dict.get('row_number', 0)
        mobile = arguments_dict.get('mobile', '')
        remarks = arguments_dict.get('remarks', '')

        if function_name == "book_schedule":
            save_response = save_booking(facebook_page_instance, row_number, fb_id, name, mobile, remarks)
            print("Save Booking Response:", save_response)
            return "🎉 Your booking has been successfully made! Thank you! 📅"

    return None