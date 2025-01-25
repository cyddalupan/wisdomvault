import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import time
import datetime

from chat.utils import get_service, summarizer

# Global variable to store the fetched data and its timestamp
cached_data = {
    'data': None,
    'timestamp': 0
}

def instruction(facebook_page_instance, target_row=None):
    global cached_data  # Use the global variable

    # Check if the cached data is older than 20 seconds
    current_time = time.time()
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
                cached_data['data'] = inventory_message
                cached_data['timestamp'] = current_time

            except Exception as e:
                return f"Error fetching inventory data: {e}"

    else:
        print("Using cached data...")

    return (
        f"Manage users' sales: Record purchases made by customers involving one or more items. "
        f"Use the 'create_sale' function to process transactions. Before completing the sale, confirm the details: "
        f"Total cost and list of products being purchased. For reference, here is the active inventory stored on Google Sheets:\n"
        f"{cached_data['data']}\n\n"
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
            is_success = create_sale(facebook_page_instance.sheet_id, arguments_dict)
            if is_success:
                summarizer(user_profile)
                return "📃"
        
    return None

def create_sale(sheet_id, arguments_dict):
    print("create_sale dict", arguments_dict)
    # Example value of arguments_dict
    # {'items': [{'row_number': 4, 'quantity': 2}, {'row_number': 5, 'quantity': 2}, {'row_number': 6, 'quantity': 10}], 'confirmation': True}

    # Initialize Google Sheets API service
    service = get_service()

    # Prepare to track the total sale amount and generate the sale details
    total_sale = 0
    sales_data = []
    sale_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current date and time for sale

    # Iterate through the items in the sale to calculate total and prepare data
    for item in arguments_dict.get('items', []):
        row_number = item.get('row_number')
        quantity = item.get('quantity')

        # Get product details from inventory
        inventory_data = get_product_data_from_inventory(sheet_id, row_number)  # Helper function to get product details by row number

        if inventory_data:
            product_name = inventory_data.get('name')
            price = inventory_data.get('price')
            stock = inventory_data.get('stocks')
            
            # Check if there is enough stock for the sale
            if stock < quantity:
                print(f"Not enough stock for {product_name}. Available: {stock}, Required: {quantity}")
                return False  # If not enough stock, return an error
                
            total_amount = price * quantity
            total_sale += total_amount

            # Prepare data for Sales sheet (one row per item)
            sales_data.append([sale_time, product_name, quantity, total_amount])

            # Deduct stock from the Inventory sheet
            new_stock = stock - quantity
            update_inventory_stock(sheet_id, row_number, new_stock)

    # Step 1: Insert data into the 'Sales' sheet
    try:
        response_sales = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Sales",  # The range where we want to append the data (automatically adds to the end)
            valueInputOption="USER_ENTERED",
            body={
                "values": sales_data
            }
        ).execute()
        
        print(f"Sale data added to 'Sales' sheet successfully.")
    except Exception as e:
        print(f"Error adding sale data to 'Sales' sheet: {e}")
        return False

    # Step 2: Insert summary data into the 'Sales Summary' sheet
    try:
        # Insert sale summary (one row per batch sale)
        sale_summary_data = [[sale_time, total_sale]]

        response_summary = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Sales Summary",  # Range for Sales Summary sheet
            valueInputOption="USER_ENTERED",
            body={
                "values": sale_summary_data
            }
        ).execute()

        print(f"Sale summary added to 'Sales Summary' sheet successfully.")
    except Exception as e:
        print(f"Error adding sale summary to 'Sales Summary' sheet: {e}")
        return False

    return True


def get_product_data_from_inventory(sheet_id, row_number):
    service = get_service()

    # Get the specific row data from the Inventory sheet
    range_ = f"Inventory!A{row_number}:E{row_number}"  # Adjust this range if needed
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_
    ).execute()

    values = result.get('values', [])
    
    # Check if data exists for the row
    if values:
        # If data is found, retrieve the current row or default to an empty string if a column is missing
        current_row = values[0]  # This is a list with 5 expected columns: Product Code, Name, Stocks, Price, Description
        
        # Prepare the data, using current values if the new value is not provided
        product_code = current_row[0] if len(current_row) > 0 else None
        name = current_row[1] if len(current_row) > 1 else None
        stocks = int(current_row[2]) if len(current_row) > 2 and current_row[2] else 0
        price = float(current_row[3]) if len(current_row) > 3 and current_row[3] else 0.0
        description = current_row[4] if len(current_row) > 4 else None

        # Return a dictionary with the complete data (using current values where necessary)
        return {
            'product_code': product_code,
            'name': name,
            'stocks': stocks,
            'price': price,
            'description': description
        }
    else:
        # If no data found, log and return None
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
