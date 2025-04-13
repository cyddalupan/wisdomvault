import json
import time
from datetime import date

from chat.cache import delete_cache, get_cache, update_cache
from chat.service import get_service
from chat.utils import summarizer

cache_type = "inventory_admin"

def instruction(facebook_page_instance, target_row=None):
    # Check if the cached data is older than 20 seconds
    current_time = time.time()
    page_id = facebook_page_instance.page_id
    cached_data = get_cache(page_id, cache_type)
    print("### cached_data ***", cached_data)
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

    print("### cached_data", cached_data)
    return (
        "Manage users inventory. "
        "IMPORTANT: Never ask user what row number an item is. if row number does not exist it means item does not exist. "
        "IMPORTANT: The Google Sheet is the sole source of truth regarding inventory data. "
        f"Here are the items stored on Google Sheets:\n{cached_data['data']}\n\n "
    )

def generate_tools():
    tools = []

    tools.append({
        "type": "function",
        "function": {
            "name": "delete_row",
            "description": "delete one row from SpreadSheet",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirmation": {
                        "type": "boolean",
                        "description": "user confirms that the product will be deleted",
                    },
                    "item_name": {
                        "type": "string",
                        "description": "name of item/product",
                    },
                },
                "required": ["item_name", "confirmation"],
            },
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "add_row",
            "description": "add one row, unique data from SpreadSheet",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_code": {
                        "type": "string",
                        "description": "unique code - optional",
                    },
                    "name": {
                        "type": "string",
                        "description": "item or product name",
                    },
                    "stocks": {
                        "type": "integer",
                        "description": "how many items are left",
                    },
                    "price": {
                        "type": "integer",
                        "description": "how much is the item",
                    },
                    "desciprtion": {
                        "type": "string",
                        "description": "product description - optional",
                    },
                },
                "required": ["name", "stocks", "price"],
            },
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "edit_row",
            "description": "edit or update one row from SpreadSheet",
            "parameters": {
                "type": "object",
                "properties": {
                    "row_number": {
                        "type": "integer",
                        "description": "row number of the product to edit based on Google Sheet data.",
                    },
                    "product_code": {
                        "type": "string",
                        "description": "unique code",
                    },
                    "name": {
                        "type": "string",
                        "description": "item or product name",
                    },
                    "stocks": {
                        "type": "integer",
                        "description": "how many items are left",
                    },
                    "price": {
                        "type": "integer",
                        "description": "how much is the item",
                    },
                    "description": {
                        "type": "string",
                        "description": "product description",
                    },
                },
                "required": ["row_number"],
            },
        }
    })

    return tools

def tool_function(tool_calls, user_profile, facebook_page_instance):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        if function_name == "delete_row":
            item_name = arguments_dict.get('item_name')
            confirmation = arguments_dict.get('confirmation', False)
            if confirmation and item_name:
                is_success = delete_row(facebook_page_instance.sheet_id, item_name, facebook_page_instance.page_id)
                if is_success:
                    summarizer(user_profile)
                    return f"🗑️{item_name} - Deleted"
        
        if function_name == "add_row":
            is_success = add_row(facebook_page_instance.sheet_id, arguments_dict, facebook_page_instance.page_id)
            name = arguments_dict.get('name')
            if is_success:
                summarizer(user_profile)
                return f"✅{name} - Added"
        
        if function_name == "edit_row":
            is_success = edit_row(facebook_page_instance.sheet_id, arguments_dict, facebook_page_instance.page_id)
            if is_success:
                summarizer(user_profile)
                return f"✏️Product Updated"
    return None

def delete_row(sheet_id, product_name, page_id):
    service = get_service()

    try:
        # Prepare log entry for deletion in Inventory_Logs
        today = date.today().isoformat()
        log_entry = [[today, product_name, "Deleted", "True"]]

        # Append the deletion log to Inventory_Logs
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Inventory_Logs",
            valueInputOption="USER_ENTERED",
            body={"values": log_entry}
        ).execute()

        delete_cache(page_id, cache_type)
        return True

    except Exception as e:
        print(f"Error logging deletion: {e}")
        return False

def add_row(sheet_id, arguments_dict, page_id):
    name = arguments_dict.get('name', "")
    fields_to_log = {
        'Product Code': arguments_dict.get('product_code', ""),
        'Stocks': arguments_dict.get('stocks', None),
        'Price': arguments_dict.get('price', None),
        'Description': arguments_dict.get('description', ""),
    }
    fields_to_log = {k: v for k, v in fields_to_log.items() if v is not None and v != ""}  # Filter out empty values

    service = get_service()
    today = date.today().isoformat()  # Gets today's date in 'YYYY-MM-DD' format
    new_rows = []

    # Add initial log for product name creation
    if name:
        new_rows.append([today, "", "Name", name])

    # Add logs for other fields
    for column, value in fields_to_log.items():
        new_rows.append([today, name, column, value])

    try:
        # Use the values.append() method to append the new rows at the end
        response = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Inventory_Logs", 
            valueInputOption="USER_ENTERED",
            body={"values": new_rows}
        ).execute()

        print("Row added successfully.")
        delete_cache(page_id, cache_type)
        return True

    except Exception as e:
        print(f"Error adding rows: {e}")
        return False

def edit_row(sheet_id, arguments_dict, page_id):
    row_number = arguments_dict.get('row_number') 
    name = arguments_dict.get('name', None)
    product_code = arguments_dict.get('product_code', None)
    stocks = arguments_dict.get('stocks', None)
    price = arguments_dict.get('price', None)
    description = arguments_dict.get('description', None)
    
    # Ensure row_number is provided and is a valid integer
    if row_number is None:
        return False

    service = get_service()

    try:
        # Subtract 1 because Google Sheets API uses 0-based indexing for rows
        row_index = row_number - 1

        # Read the current row data to preserve any values not being updated
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"Inventory!A{row_index + 1}:E{row_index + 1}"
        ).execute()

        # Retrieve the current row, or default to an empty list if not found
        current_row = result.get('values', [[]])[0]

        # Clean and validate stocks and price
        def clean_number(value):
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        stocks = clean_number(stocks if stocks is not None else current_row[2] if len(current_row) > 2 else None)
        price = clean_number(price if price is not None else current_row[3] if len(current_row) > 3 else None)

        # Prepare the new row data to be updated
        updated_values = [
            name if name is not None else current_row[0] if len(current_row) > 0 else None,
            product_code if product_code is not None else current_row[1] if len(current_row) > 1 else None,
            stocks,
            price,
            description if description is not None else current_row[4] if len(current_row) > 4 else None
        ]

        # Update the row in the spreadsheet
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"Inventory!A{row_index + 1}:E{row_index + 1}",
            valueInputOption="USER_ENTERED",
            body={"values": [updated_values]}
        ).execute()

        delete_cache(page_id, cache_type)
        return True

    except Exception as e:
        return False