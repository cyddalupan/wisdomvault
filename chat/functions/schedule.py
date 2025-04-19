import time
import json
from datetime import datetime

from chat.cache import get_cache, update_cache
from chat.service import get_service

# Global variable for caching
cache_all = "schedule_all"
cache_available = "schedule_available"
cache_booking = "schedule_booking"

def read_bookings(facebook_page_instance):
    # Check if the cached data is older than 20 seconds
    current_time = time.time()
    page_id = facebook_page_instance.page_id
    cached_data = get_cache(page_id, cache_all)
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
                cached_data = update_cache(page_id, cache_all, bookings_message)

            except Exception as e:
                return f"Error fetching bookings data: {e}"

    return cached_data['data']

def available_schedule(facebook_page_instance):
    # Check if the cached data is older than 20 seconds
    current_time = time.time()
    page_id = facebook_page_instance.page_id
    cached_data = get_cache(page_id, cache_available)
    if current_time - cached_data['timestamp'] > 20:
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

                    # Start processing from the 7th row in the sheet.
                    start_from_row = 7
                    for i, row in enumerate(values[6:], start=start_from_row):
                        # Check if the second column (date) exists and is not empty
                        date_str = row[2] if len(row) > 2 else None
                        name = row[5] if len(row) > 5 else None

                        if date_str and name is None:  # Only proceed if there's a date and no name
                            date = datetime.strptime(date_str, '%Y-%m-%d')
                            if date > current_date:
                                available_message += f"Row {i}: {date_str}, {row[3]} (FB_ID: {row[4] if len(row) > 4 else 'N/A'})\n"

                # Cache the data and timestamp
                cached_data = update_cache(page_id, cache_available, available_message)

            except Exception as e:
                return f"Error fetching available schedules: {e}"

    return cached_data['data']

def get_booking_date(facebook_page_instance, fb_id):
    # Check if the cached data is older than 30 seconds
    current_time = time.time()
    page_id = facebook_page_instance.page_id
    cached_data = get_cache(page_id, cache_booking)
    if current_time - cached_data['timestamp'] > 30:
        print("Fetching bookings from Google Sheets...")
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
                bookings = {}

                if values:
                    current_date = datetime.now()

                    for row in values[6:]:  # Assuming the first six rows are headers
                        # Check if the second column (date) and fifth column (fb_id) exist
                        date_str = row[2] if len(row) > 2 else None
                        fb_id_cell = row[4] if len(row) > 4 else None

                        if date_str and fb_id_cell:  # Proceed if there's a date and an fb_id
                            date = datetime.strptime(date_str, '%Y-%m-%d')
                            if date >= current_date:
                                bookings[fb_id_cell] = date_str

                # Cache the bookings data and timestamp
                cached_data = update_cache(page_id, cache_booking, bookings)

            except Exception as e:
                print(f"Error fetching bookings: {e}")
                cached_data['data'] = {}

    # Return the booking date if it exists
    return cached_data['data'].get(fb_id, None)

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

def cancel_booking(facebook_page_instance, fb_id):
    if facebook_page_instance and getattr(facebook_page_instance, 'sheet_id', None):
        sheet_id = facebook_page_instance.sheet_id

        try:
            # Initialize the Sheets API service
            service = get_service()

            # Retrieve all rows in the bookings sheet
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range="Bookings!A2:H"
            ).execute()

            # Get the list of rows (values)
            rows = result.get('values', [])

            # Current date for comparison
            today = datetime.now().date()

            for i, row in enumerate(rows, start=2):  # start=2 to account for the actual row number in the sheet
                if len(row) < 5:
                    continue  # Skip incomplete rows
                
                # Extract date and fb_id from the row
                booking_date_str = row[2]  # Assuming the date is in column C
                current_fb_id = row[4]  # Assuming fb_id is in column E

                # Parse the date from the spreadsheet
                try:
                    booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue  # Skip rows with invalid dates

                # Check if the date is in the future and fb_id matches
                if booking_date > today and current_fb_id == fb_id:
                    # Prepare the updated row data indicating cancellation
                    updated_values = [
                        row[0],  # Keep existing value in column A
                        row[1],  # Keep existing value in column B
                        row[2],  # Keep existing value in column C (Date)
                        row[3],  # Keep existing value in column D (Time)
                        "",      # Clear FB_ID
                        "",      # Clear Name
                        "",      # Clear Mobile
                        ""       # Clear Remarks
                    ]

                    # Prepare the request body for the update
                    body = {
                        'values': [updated_values]
                    }

                    # Update the row in the spreadsheet
                    service.spreadsheets().values().update(
                        spreadsheetId=sheet_id,
                        range=f"Bookings!A{i}:H{i}",
                        valueInputOption="USER_ENTERED",
                        body=body
                    ).execute()

                    return f"Booking cancelled for fb_id {fb_id} on row {i}."

            return "No future booking found with the given fb_id."

        except Exception as e:
            return f"Error cancelling booking: {e}"
    else:
        return "Facebook page instance or sheet_id is missing."

def instruction(facebook_page_instance, facebook_id):
    booking_date_str = get_booking_date(facebook_page_instance, facebook_id)
    schedules = available_schedule(facebook_page_instance)
    current_datetime = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    if booking_date_str:
        # Parse the existing booking date
        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d')
        days_until_booking = (booking_date - datetime.now()).days
        
        if days_until_booking > 2:
            return (f"\nINSTRUCTION: The user already has a booking scheduled on {booking_date_str}. "
                    f"If the user wishes to cancel, inform them that they can do so since the booking is more than 2 days from today. "
                    f"Trigger the 'cancel_booking' tool function to facilitate the cancellation. "
                    f"Ensure cancellations happen at least 2 days in advance of the booking date.")
        else:
            return (f"\nINSTRUCTION: The user already has a booking scheduled on {booking_date_str}. "
                    f"Do not offer cancellations since the booking is within 2 days. "
                    f"Advise the user to adhere to their scheduled appointment.")
    else:
        return (f"\nINSTRUCTION: If the conversation lacks context or direction, suggest booking a schedule. "
                f"Advise the user not to visit without a schedule; booking is required. "
                f"Only offer schedules that are listed in the available schedules. "
                f"Inform the user about the unavailability of schedules if none exist, and suggest trying again later. "
                f"Provide the current date and time: {current_datetime}. "
                f"Recommend an available schedule from the gathered list. "
                f"Collect necessary details such as date, time, mobile number, and optional remarks. "
                f"Use the 'book_schedule' tool function to assist in booking schedules. "
                f"\n\nAvailable schedules from Google Sheets:\n{schedules}")

def generate_tools(facebook_page_instance, facebook_id):
    booking_date_str = get_booking_date(facebook_page_instance, facebook_id)

    if booking_date_str:
        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d')
        days_until_booking = (booking_date - datetime.now()).days
        if days_until_booking > 2:
            return {
                "type": "function",
                    "function": {
                        "name": "cancel_booking",
                        "description": "cancel users booking.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "confirmation": {
                                    "type": "boolean",
                                    "description": "user confirms to cancel booking",
                                },
                            },
                            "required": ["confirmation"],
                        },
                    }
                }
        else:
            return None
    else:
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
        row_number = arguments_dict.get('row_number', 0) - 1;
        mobile = arguments_dict.get('mobile', '')
        remarks = arguments_dict.get('remarks', '')
        confirmation = arguments_dict.get('confirmation', False)

        if function_name == "book_schedule":
            save_response = save_booking(facebook_page_instance, row_number, fb_id, name, mobile, remarks)
            print("Save Booking Response:", save_response)
            return "🎉 Your booking has been successfully made! Thank you! 📅"
        
        if function_name == "cancel_booking":
            if confirmation:
                save_response = cancel_booking(facebook_page_instance, fb_id)
                print("Cancel Booking Response:", save_response)
                return "✅ Your booking cancellation was successful!"
    return None