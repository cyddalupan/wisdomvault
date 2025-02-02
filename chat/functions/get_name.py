import json


def get_name_instruction(user_profile):
    # Check if user_profile.name exists

    return ('Before proceeding with any task, prioritize asking for the user\'s name. '
    'Since this is running on Facebook Messenger, users might assume you already know their name. '
    'Politely ask for their real name. sometimes user dont use real name on facebook. '
    'Trigger save_name funtction when user give name' if not user_profile.name else '')

def get_name_generate_tools():
    return ({
        "type": "function",
        "function": {
            "name": "save_name",
            "description": "get name of user",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "name of user."
                    },
                },
                "required": ["name"],
            },
        }
    })

def get_name_tool_function(tool_calls, user_profile):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        if function_name == "save_name":
            name = arguments_dict.get('name')
            user_profile.name = name
            user_profile.save()