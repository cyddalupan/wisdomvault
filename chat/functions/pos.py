import json
import time
import datetime

from chat.cache import get_cache, update_cache
from chat.service import get_service
from chat.utils import summarizer


cache_type = "pos"

def instruction(facebook_page_instance, target_row=None):
    current_time = time.time()
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

    # get updated cache data
    return (
        f"Manage users' sales: Record purchases made by customers involving one or more items. "
        f"Use the 'create_sale' function to process transactions. Before completing the sale, confirm the details: "
        f"Total cost and list of products being purchased. For reference, here is the active inventory stored on Google Sheets:\n"
        f"{cached_data['data']}\n\n"
        "IMPORTANT: The Google Sheet is the sole source of truth regarding inventory data. "
        "IMPORTANT: You are talking to the user which is the business owner, The user is selling and not buying and we will record what user sells. "
        f"Please review the products and total cost, and confirm if you'd like to proceed with the sale."
        "Do not sell if stocks is not enough."
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
                        "description": "List of items to be sold with their quantities, identified by inventory name.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "name of the product.",
                                },
                                "price": {
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
                    "remarks": {
                        "type": "string",
                        "description": "Optional remarks.",
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
            is_success = create_sale(facebook_page_instance.sheet_id, arguments_dict, arguments_dict.get('customer'))
            if is_success:
                summarizer(user_profile)
                return "📃Order Has been created!"
        
    return None

def create_sale(sheet_id, arguments_dict, remarks):
    print("create_sale dict", arguments_dict)
    service = get_service()

    sales_data = []
    sale_time = datetime.date.today().isoformat()  # Use today's date

    for item in arguments_dict.get('items', []):
        name = item.get('name')
        quantity = item.get('quantity')

        # Prepare data for Sales_Logs sheet
        sales_data.append([True, sale_time, name, quantity, remarks])

    def find_next_empty_row_in_column(sheet_id, sheet_name, column):
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!{column}:{column}"
        ).execute()

        values = result.get('values', [])
        for i, cell in enumerate(values):
            if len(cell) == 0 or cell[0].strip() == "":
                return i + 1

        return len(values) + 1

    next_sales_row = find_next_empty_row_in_column(sheet_id, "Sales_Logs", "B")

    try:
        response_sales = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"Sales_Logs!A{next_sales_row}",
            valueInputOption="USER_ENTERED",
            body={"values": sales_data}
        ).execute()
        
        print("Sale data added to 'Sales_Logs' sheet successfully.")
    except Exception as e:
        print(f"Error adding sale data to 'Sales_Logs' sheet: {e}")
        return False

    return True
