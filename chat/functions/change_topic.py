import json


def generate_tools():
    return {
        "type": "function",
        "function": {
            "name": "change_topic",
            "description": "Switch topic only when the user explicitly changes from the current task (e.g., from 'inventory' to 'POS').",
            "parameters": {
                "type": "object",
                "properties": {
                    "new_topic": {
                        "type": "string",
                        "enum": ["inventory", "pos", "other"],
                        "description": "The new topic to switch to."
                    }
                },
                "required": ["new_topic"]
            }
        }
    }

def tool_function(tool_calls, user_profile):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        if function_name == "change_topic":
            new_topic = arguments_dict.get('new_topic')
            user_profile.task = new_topic
            user_profile.save()
    return None