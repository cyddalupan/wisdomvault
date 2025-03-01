import json
import time

from chat.cache import get_cache, update_cache
from chat.functions.pos import create_sale
from chat.utils import get_service, summarizer

def instruction(facebook_page_instance, target_row=None):
    # Check if the cached data is older than 20 seconds
    current_time = time.time()
    cache_type = "inventory_sheet"
    page_id = facebook_page_instance.page_id
    cached_data = get_cache(page_id, cache_type)
    if current_time - cached_data['timestamp'] > 20:
        print("Fetching new data from Google Sheets...")
        if facebook_page_instance and getattr(facebook_page_instance, 'sheet_id', None):
            sheet_id = facebook_page_instance.sheet_id

            try:
                # Initialize the Sheets API service
                service = get_service()

                # Read the data from the "Inventory" sheet
                result = service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range="Inventory"
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

    business_info = facebook_page_instance.info or "No business information provided."
    additional_info = facebook_page_instance.additional_info or "No additional information provided."
    inventory = get_cache(page_id, cache_type)['data']

    # Combine business info with the marketing message
    return (
        f"Information: {business_info}\n"
        f"Additional Info: {additional_info}\n"
        + (
            f"Live Inventory:\n{inventory}\n\n"
            f"For reference, this is the active inventory stored on Google Sheets.\n\n"
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
                                "row_number": {
                                    "type": "integer",
                                    "description": "Row number in the inventory sheet for the product.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "Quantity of the product being sold.",
                                },
                            },
                            "required": ["row_number", "quantity"],
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
            is_success = create_sale(facebook_page_instance.sheet_id, arguments_dict, user_profile.name)
            if is_success:
                summarizer(user_profile)
                return "📃Order Created, Please send payment confirmation, Salamat"
        
    return None