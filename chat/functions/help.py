import json


def generate_tools():
    return {
        "type": "function",
        "function": {
            "name": "help",
            "description": "if the system does not know what to say, ask admin what to say",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A structured question based on what user is saying and asking"
                    }
                },
                "required": ["question"]
            }
        }
    }

def tool_function(tool_calls, user_profile):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        if function_name == "help":
            question = arguments_dict.get('question')
            # TODO: Logic for saving question
            return question
            # user_profile.task = question
            # user_profile.save()
    return None