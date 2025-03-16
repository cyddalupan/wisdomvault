from chat.functions import leads, schedule, help

def trigger_tool_calls(first_run, tool_calls, user_profile, facebook_page_instance, tool_function):
    if first_run and any(tool_call.function.name == "ask_manager_help" for tool_call in tool_calls):
        response_content = help.tool_function(tool_calls, user_profile)
    elif first_run and any(tool_call.function.name == "save_user_info" for tool_call in tool_calls):
        response_content = leads.save_user_info(tool_calls, user_profile, facebook_page_instance)
    elif first_run and any(tool_call.function.name == "book_schedule" for tool_call in tool_calls):
        response_content = schedule.book_schedule(tool_calls, user_profile, facebook_page_instance)
    elif tool_function:
        response_content = tool_function(tool_calls, user_profile, facebook_page_instance)

    return response_content

