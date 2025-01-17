import json


def generate_tools():
    return {
        "type": "function",
        "function": {
            "name": "help",
            "description": "if the system does not know what to say, use this to ask admin what to say",
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
            # Save the question into the Help model
            help_entry = Help.objects.create(
                page_id=user_profile.page_id,
                fb_id=user_profile.facebook_id,
                name=user_profile.name,
                question=question,
                answer=None  # Leave blank initially; answer can be filled later
            )
            return f"Your question has been recorded: {question}"
    return None
