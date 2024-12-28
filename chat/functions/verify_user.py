
import json


def instruction():
    return "ask for users full name because maybe name in facebook is different"

def generate_tools():
    tools = []

    tools.append({
        "type": "function",
        "function": {
            "name": "save_name",
            "description": "save name of user",
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {
                        "type": "string",
                        "description": "user full name",
                    },
                },
                "required": ["full_name"],
            },
        }
    })

    return tools

def tool_function(tool_calls, user_profile, facebook_page_instance):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        # Validation before saving data
        if function_name == "save_name":
            full_name = arguments_dict.get('full_name', '')
            if isinstance(full_name, str) and len(full_name) <= 255:
                user_profile.full_name = full_name
            else:
                return "The name format seems wrong or too long"

    # Save updated user profile in Django without errors
    user_profile.task = ""
    user_profile.save()
    return None

# def generate_tools(user_profile):
#     tools = []

#     # Special case for full_name
#     if not user_profile.full_name or user_profile.full_name == "Facebook User":
#         tools.append({
#             "type": "function",
#             "function": {
#                 "name": "save_name",
#                 "description": "save name of user",
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "full_name": {
#                             "type": "string",
#                             "description": "user full name",
#                         },
#                     },
#                     "required": ["full_name"],
#                 },
#             }
#         })

#     # Other fields
#     fields = [
#             {"field": "age", "function_name": "save_age", "description": "save age of user", "parameter_type": "string", "parameter_name": "age", "var_desc": "users age"},
#             {"field": "contact_number", "function_name": "save_contact_number", "description": "save contact number of user. make sure this is a valid philippine number", "parameter_type": "string", "parameter_name": "contact_number", "var_desc": "users philippine contact number only"},
#             {"field": "whatsapp_number", "function_name": "save_whatsapp_number", "description": "save whatsapp number of user", "parameter_type": "string", "parameter_name": "whatsapp_number", "var_desc": "users whatsapp number"},
#             {"field": "location", "function_name": "save_location", "description": "save users valid complete philippine address", "parameter_type": "string", "parameter_name": "location", "var_desc": "users valid complete address in the philippines only"},
#     ]

#     for field_info in fields:
#         if not getattr(user_profile, field_info["field"]):
#             tools.append({
#                 "type": "function",
#                 "function": {
#                     "name": field_info["function_name"],
#                     "strict": True,
#                     "description": field_info["description"],
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             field_info["parameter_name"]: {
#                                 "type": field_info["parameter_type"],
#                                 "description": field_info["var_desc"],
#                             },
#                         },
#                         "required": [field_info["parameter_name"]],
#                         "additionalProperties": False,
#                     },
#                 }
#             })

#     if len(tools) == 0:
#         return None

#     return tools