import json

from chat.utils import get_possible_topics, summarize_sales, summarizer


def generate_tools(facebook_page_instance):
    available_topics = get_possible_topics(facebook_page_instance)

    return {
        "type": "function",
        "function": {
            "name": "change_topic",
            "description": (
                "Switch the topic immediately if the user mentions something related to a different task. "
                "For instance, if the user is talking about inventory but then mentions a sale (e.g., 'we got an order'), "
                "switch to sales without the user needing to explicitly say so. "
                f"The following topics are available: {', '.join(available_topics)}. "
                "If the user refers to a different task or shifts focus (like inventory to sales), switch to the relevant topic. "
                "Only handle the tasks listed in the available topics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "new_topic": {
                        "type": "string",
                        "enum": available_topics,
                        "description": "The new topic to switch to. This must be one of the available topics."
                    }
                },
                "required": ["new_topic"]
            }
        }
    }


def tool_function(tool_calls, user_profile, facebook_page_instance):
    available_topics = get_possible_topics(facebook_page_instance)

    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        if function_name == "change_topic":
            print("change_topic")
            new_topic = arguments_dict.get('new_topic')

            if new_topic in available_topics:  # Ensure the topic is enabled before switching
                if new_topic == 'analyze':
                    summarize_sales(facebook_page_instance)
                
                user_profile.task = new_topic
                user_profile.save()
                print("trigger summarizer")
                summarizer(user_profile)
            else:
                print(f"Topic {new_topic} is not enabled, ignoring request.")

    return None
