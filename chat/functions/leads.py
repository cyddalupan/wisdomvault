import json

from chat.service import get_service

def instruction():
    return "\nYour Main Role is to Aggressively and proactively collect and ensure the user provides their mobile number, gender, area, and birthday. This information is mandatory, and its importance should be communicated clearly and respectfully. Once obtained, trigger the `save_user_info` function."

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
                        "description": "users birthdate, require year",
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
                        range="Leads!A2:G",  # Assuming these are the required columns
                        valueInputOption="USER_ENTERED",
                        insertDataOption='INSERT_ROWS',
                        body={"values": new_row}
                    ).execute()
                    
                    user_profile.is_leads_complete = True
                    user_profile.sms = mobile
                    user_profile.save()

                    print("User information saved successfully.")
                    return "Salamat. ano pa ang matutulong ko sayo?"

                except Exception as e:
                    print(f"Error saving user information: {e}")
                    return False

    return None