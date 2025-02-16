def instruction(facebook_page_instance, target_row=None):
    sales_summary = facebook_page_instance.sales

    return (
        f"Analize Data: User wants information about recent sales."
        f"Summary of recent transactions: {sales_summary}"
    )

def generate_tools():
    return None


def tool_function(tool_calls, user_profile, facebook_page_instance):
    return None
