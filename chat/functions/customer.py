import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

def instruction(facebook_page_instance, target_row=None):
    business_info = facebook_page_instance.info
    additional_info = facebook_page_instance.additional_info
    marketing_message = (
        "Focus on promoting our product or business actively while engaging the user in a meaningful way to keep the conversation interactive. "
        "If you are unsure or do not have accurate information, never assume or invent anything. Instead, trigger the help function immediately for assistance."
    )

    # TODO: Add inventories for selling
    # TODO: Add Additional info

    # Combine business info with the marketing message
    return f"{marketing_message}\nInfo: {business_info}\nAdditional Info: {additional_info}"


def generate_tools():
    tools = []

    # tools.append({
    #     "type": "function",
    #     "function": {
    #         "name": "delete_row",
    #         "description": "delete one row from SpreadSheet",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "confirmation": {
    #                     "type": "boolean",
    #                     "description": "user confirms that the product will be deleted",
    #                 },
    #                 "row_number": {
    #                     "type": "integer",
    #                     "description": "row of the product to delete",
    #                 },
    #             },
    #             "required": ["row_number", "confirmation"],
    #         },
    #     }
    # })

    return tools

def tool_function(tool_calls, user_profile, facebook_page_instance):
    # for tool_call in tool_calls:
    #     function_name = tool_call.function.name
    #     arguments = tool_call.function.arguments
    #     arguments_dict = json.loads(arguments)

    #     if function_name == "delete_row":
    #         row_number = arguments_dict.get('row_number')
    #         confirmation = arguments_dict.get('confirmation', False)
    #         if confirmation and row_number:
    #             is_success = delete_row(facebook_page_instance.sheet_id, row_number)
    #             if is_success:
    #                 return "Row Deleted. What else can I help you?"
        
    #     if function_name == "add_row":
    #         is_success = add_row(facebook_page_instance.sheet_id, arguments_dict)
    #         if is_success:
    #             return "Row Added. What else can I help you?"
        
    #     if function_name == "edit_row":
    #         is_success = edit_row(facebook_page_instance.sheet_id, arguments_dict)
    #         if is_success:
    #             return "Row Updated. What else can I help you?"
    return None
