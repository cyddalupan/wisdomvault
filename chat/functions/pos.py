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
                    "customer": {
                        "type": "string",
                        "description": "Optional name of customer.",
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

def create_sale(sheet_id, arguments_dict, name):
    print("create_sale dict", arguments_dict)
    # Initialize Google Sheets API service
    service = get_service()

    # Prepare to track the total sale amount
    total_sale = 0
    sales_data = []
    sale_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current date and time for sale

    # Iterate through the items in the sale to calculate total and prepare data
    for item in arguments_dict.get('items', []):
        row_number = item.get('row_number')
        quantity = item.get('quantity')

        # Get product details from inventory
        inventory_data = get_product_data_from_inventory(sheet_id, row_number)

        if inventory_data:
            product_name = inventory_data.get('name')
            price = inventory_data.get('price')
            stock = inventory_data.get('stocks')
            
            # Check if there is enough stock for the sale
            if stock < quantity:
                print(f"Not enough stock for {product_name}. Available: {stock}, Required: {quantity}")
                return False  # If not enough stock, return an error
                
            live_cost = price * quantity
            total_sale += live_cost

            # Prepare data for Sales sheet
            sales_data.append([sale_time, product_name, quantity, live_cost, "Done"])

            # Deduct stock from the Inventory sheet
            new_stock = stock - quantity
            update_inventory_stock(sheet_id, row_number, new_stock)

    # Helper function to retrieve next truly empty row in the specified column
    def find_next_empty_row_in_column(sheet_id, sheet_name, column):
        # Fetch all values in the specified column
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!{column}:{column}"
        ).execute()

        values = result.get('values', [])
        
        # Iterate over each row to find a truly empty spot for input
        for i, cell in enumerate(values):
            # Check for rows that are effectively empty: no content or only whitespace in column A
            if len(cell) == 0 or cell[0].strip() == "":
                return i + 1

        # If no empty cell found, return the next row after the last found row with content
        return len(values) + 1

    # Find next empty row in Sales and Transactions sheets
    next_sales_row = find_next_empty_row_in_column(sheet_id, "Sales", "A")
    next_transactions_row = find_next_empty_row_in_column(sheet_id, "Transactions", "A")

    # Step 1: Insert data into the 'Sales' sheet
    try:
        response_sales = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"Sales!A{next_sales_row}",
            valueInputOption="USER_ENTERED",
            body={"values": sales_data}
        ).execute()
        
        print("Sale data added to 'Sales' sheet successfully.")
    except Exception as e:
        print(f"Error adding sale data to 'Sales' sheet: {e}")
        return False

    # Step 2: Insert summary data into the 'Transactions' sheet
    try:
        # Insert transaction summary
        transaction_data = [[sale_time, total_sale]]

        response_summary = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"Transactions!A{next_transactions_row}",
            valueInputOption="USER_ENTERED",
            body={"values": transaction_data}
        ).execute()

        print("Sale summary added to 'Transactions' sheet successfully.")
    except Exception as e:
        print(f"Error adding sale summary to 'Transactions' sheet: {e}")
        return False

    return True

def get_product_data_from_inventory(sheet_id, row_number):
    service = get_service()

    # Get the specific row data from the Inventory sheet
    range_ = f"Inventory!A{row_number}:E{row_number}"
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_
        ).execute()
    except Exception as e:
        print(f"Error retrieving data: {e}")
        return None

    values = result.get('values', [])
    
    if values:
        current_row = values[0]
        name = current_row[0] if len(current_row) > 0 else None
        product_code = current_row[1] if len(current_row) > 1 else None
        stocks = int(current_row[2]) if len(current_row) > 2 and current_row[2] else 0

        price_str = current_row[3] if len(current_row) > 3 and current_row[3] else "0"
        try:
            price = float(''.join(filter(lambda x: x.isdigit() or x == '.', price_str)))
        except ValueError:
            price = 0.0

        description = current_row[4] if len(current_row) > 4 else None

        return {
            'name': name,
            'product_code': product_code,
            'stocks': stocks,
            'price': price,
            'description': description
        }
    else:
        print(f"No data found for row {row_number}.")
        return None

def update_inventory_stock(sheet_id, row_number, new_stock):
    service = get_service()

    # Update the stock value in the Inventory sheet
    range_ = f"Inventory!C{row_number}"  # Column C is for stock
    body = {
        "values": [[new_stock]]
    }

    try:
        response = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()

        print(f"Stock for row {row_number} updated successfully.")
    except Exception as e:
        print(f"Error updating stock in Inventory sheet: {e}")
        return False

    return True
