import json

from chat.functions.customer import get_business_info
from chat.service import get_service

def instruction():
    return "\nCollect the user's mobile number aggressively and proactively while also trying to obtain optional details like gender, area, and birthday. Communicate the importance of the mobile number clearly and respectfully. Once the mobile number is obtained, continue to ask for additional details. Only trigger the `save_user_info` function when it is clear that no more details will be provided. If the user changes the topic or does not wish to provide further details after giving their mobile number, then trigger the `save_user_info` function and move on."

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
                "required": ["mobile"],
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
                    
                    info, additional_info, after_leads = get_business_info(facebook_page_instance)
                    return after_leads

                except Exception as e:
                    print(f"Error saving user information: {e}")
                    return False

    return None