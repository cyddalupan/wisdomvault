
import json


def instruction(facebook_page_instance):
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
