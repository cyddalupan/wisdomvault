import json
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from google.oauth2 import service_account
import time

from chat.utils import get_service

import time

# This global cache will hold user data with fb_id as keys
cached_user_data = {}

def get_user_details(facebook_page_instance, fb_id):
    global cached_user_data

    current_time = time.time()

    if fb_id in cached_user_data and current_time - cached_user_data[fb_id]['timestamp'] < 60:
        print("Using cached user data...")
        return cached_user_data[fb_id]['data']

    print("Fetching new data from Google Sheets...")

    if facebook_page_instance and getattr(facebook_page_instance, 'sheet_id', None):
        sheet_id = facebook_page_instance.sheet_id

        try:
            service = get_service()

            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range="Leads!A10:G"  # Specify the starting row and relevant columns
            ).execute()

            values = result.get('values', [])

            if not values:
                print("No data found in the 'Leads' sheet.")
                return None
            else:
                for row in values:
                    if len(row) > 0 and row[0] == fb_id:  # Check if row has at least one element
                        cached_user_data[fb_id] = {
                            'data': row,
                            'timestamp': current_time
                        }
                        return row

                cached_user_data[fb_id] = {
                    'data': None,
                    'timestamp': current_time
                }
                return None

        except Exception as e:
            print(f"Error fetching user details: {e}")
            return None

    return None
    

def instruction():
    return "\nIMPORTANT: If no relevant topic is being discussed, proactively ask the user for their information: Mobile, Gender, Area, Birthday. Trigger function save_user_info once the user provides the details."

def generate_tools():
    return {
        "type": "function",
        "function": {
            "name": "save_user_info",
            "description": "Save user information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mobile": {
                        "type": "string",
                        "description": "mobile number of the user",
                    },
                    "gender": {
                        "type": "string",
                        "description": "user's gender",
                    },
                    "area": {
                        "type": "string",
                        "description": "location or city or address of user",
                    },
                    "birthday": {
                        "type": "string",
                        "description": "users birthdate with year",
                    },
                },
                "required": ["mobile", "gender", "area", "birthday"],
            },
        }
    }


def save_user_info(tool_calls, user_profile, facebook_page_instance):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)
        fb_id = user_profile.facebook_id
        name = user_profile.name
        mobile = arguments_dict.get('mobile', '')
        gender = arguments_dict.get('gender', '')
        area = arguments_dict.get('area', '')
        birthday = arguments_dict.get('birthday', '')
        
        # The status to be put as a dropdown value
        status = "New"

        if function_name == "save_user_info":
            if facebook_page_instance and getattr(facebook_page_instance, 'sheet_id', None):
                sheet_id = facebook_page_instance.sheet_id

                try:
                    service = get_service()

                    # Prepare the new row data
                    new_row = [
                        [fb_id, name, mobile, gender, area, birthday, status]
                    ]
                    
                    # Use the values.append() method to append the new row to the "Leads" sheet,
                    # specifying that the data should append starting from row 10
                    response = service.spreadsheets().values().append(
                        spreadsheetId=sheet_id,
                        range="Leads!A10:G",  # Assuming these are the required columns
                        valueInputOption="USER_ENTERED",
                        insertDataOption='INSERT_ROWS',
                        body={"values": new_row}
                    ).execute()
                    if fb_id in cached_user_data:
                        del cached_user_data[fb_id]

                    print("User information saved successfully.")
                    return "Salamat. ano pa ang matutulong ko sayo?"

                except Exception as e:
                    print(f"Error saving user information: {e}")
                    return False

    return None