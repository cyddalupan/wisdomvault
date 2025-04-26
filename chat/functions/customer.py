import json
import time

from chat.cache import get_cache, update_cache
from chat.functions.inventory import create_sale
from chat.service import get_service
from chat.utils import summarizer


def get_business_info(facebook_page_instance):
    cache_type = "business_info"
    page_id = facebook_page_instance.page_id
    cached_data = get_cache(page_id, cache_type)
    
    # Check if the cached data is older than 20 seconds
    if time.time() - cached_data['timestamp'] > 20:
        if facebook_page_instance and getattr(facebook_page_instance, 'sheet_id', None):
            sheet_id = facebook_page_instance.sheet_id
            
            try:
                service = get_service()
                result = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range="Settings!B2:B3:B4"
                ).execute()
                
                values = result.get('values', [])
                info = values[0][0] if len(values) > 0 and len(values[0]) > 0 else ""
                additional_info = values[1][0] if len(values) > 1 and len(values[1]) > 0 else ""
                after_leads = values[2][0] if len(values) > 2 and len(values[2]) > 0 else ""
                
                # Optionally cache the new values if necessary
                update_cache(page_id, cache_type, {
                    'info': info,
                    'additional_info': additional_info,
                    'after_leads': after_leads
                })

            except Exception as e:
                return "Error fetching settings data: {}".format(e)
    else:
        info = cached_data['data'].get('info', "")
        additional_info = cached_data['data'].get('additional_info', "")
        after_leads = cached_data['data'].get('after_leads', "")
    
    return info, additional_info

def instruction(facebook_page_instance, target_row=None):
    # Check if the cached data is older than 20 seconds
    current_time = time.time()
    cache_type = "inventory_sheet"
    page_id = facebook_page_instance.page_id
    cached_data = get_cache(page_id, cache_type)
    if current_time - cached_data['timestamp'] > 20:
        if facebook_page_instance and getattr(facebook_page_instance, 'sheet_id', None):
            sheet_id = facebook_page_instance.sheet_id

            try:
                # Initialize the Sheets API service
                service = get_service()

                # Read the data from the "Inventory" sheet
                result = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range="Inventory_Data"
                ).execute()

                values = result.get('values', [])
                if not values:
                    inventory_message = "No data found in the 'Inventory' sheet."
                else:
                    # Format the sheet data into a readable string
                    inventory_message = "Live Inventory Products Data in Sheets Format:\n"
                    for i, row in enumerate(values):
                        row_info = f"Row {i + 1}: {', '.join(row)}"
                        if target_row is not None and i == target_row:
                            row_info += " <-- Target Row"
                        inventory_message += row_info + "\n"
                
                # Cache the data and timestamp
                cached_data = update_cache(page_id, cache_type, inventory_message)

            except Exception as e:
                return f"Error fetching inventory data: {e}"
    else:
        print("Using cached data...")

    
    info, additional_info, after_leads = get_business_info(facebook_page_instance)
    business_info = info or "No business information provided."
    additional_info = additional_info or "No additional information provided."
    inventory = get_cache(page_id, cache_type)['data']

    # Combine business info with the marketing message
    return (
        f"Information: {business_info}\n"
        f"Additional Info: {additional_info}\n"
        + (
            f"Live Inventory:\n{inventory}\n\n"
            f"For reference, this is the active inventory stored on Google Sheets.\n\n"
            f"We do not need to tell or sell the users about deleted products. "
            f"Use the 'sale' function if the user wants to buy. Before completing the sale, confirm the details: "
            f"Total cost and list of products being purchased.\n\n"
            f"Please review the products and total cost, and confirm if you'd like to proceed with the sale. "
            "Do not sell if stocks are not enough."
            if facebook_page_instance.is_online_selling else
            ""
        )
    )



def generate_tools():
    tools = []

    tools.append({
        "type": "function",
        "function": {
            "name": "create_sale",
            "description": "Create a sale transaction involving one or more items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "List of items to be sold with their quantities, identified by inventory row number.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "name of the product.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "Quantity of the product being sold.",
                                },
                            },
                            "required": ["name", "quantity"],
                        },
                    },
                    "confirmation": {
                        "type": "boolean",
                        "description": "User confirmation that the order is complete.",
                    },
                },
                "required": ["items", "confirmation"],
            },
        }
    })

    return tools


def tool_function(tool_calls, user_profile, facebook_page_instance):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        if function_name == "create_sale":
            remarks = "Order from Facebook by: " + user_profile.name

            is_success = create_sale(facebook_page_instance.sheet_id, arguments_dict, remarks, False)
            if is_success:
                summarizer(user_profile)
                return "📃Order Created, Please send picture of payment, Salamat"
        
    return None