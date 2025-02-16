import json
import time

from chat.cache import delete_cache, get_cache, update_cache
from chat.utils import get_service, summarizer

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
                update_cache(page_id, cache_type, inventory_message)
                cached_data = get_cache(page_id, inventory_message)

            except Exception as e:
                return f"Error fetching inventory data: {e}"

    else:
        print("Using cached data...")

    return (
        f"Manage users' inventory stored on Google Sheets:\n{cached_data['data']}\n\n"
        "IMPORTANT: The Google Sheet is the sole source of truth regarding inventory data. "
        "Never add a product that already exists in the inventory. "
        "If a product already exists, suggest editing the existing entry instead of adding a duplicate. "
        "Always verify the product details to avoid duplicates."
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
                    "row_number": {
                        "type": "integer",
                        "description": "row of the product to delete",
                    },
                    "item_name": {
                        "type": "string",
                        "description": "name of item/product",
                    },
                },
                "required": ["row_number", "confirmation"],
            },
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "add_row",
            "description": "add one row from SpreadSheet, make sure product name does not exist yet",
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
                "required": ["name"],
            },
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "edit_row",
            "description": "edit one row from SpreadSheet",
            "parameters": {
                "type": "object",
                "properties": {
                    "row_number": {
                        "type": "integer",
                        "description": "row of the product to delete",
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
            row_number = arguments_dict.get('row_number')
            item_name = arguments_dict.get('item_name')
            confirmation = arguments_dict.get('confirmation', False)
            if confirmation and row_number:
                is_success = delete_row(facebook_page_instance.sheet_id, row_number, facebook_page_instance.page_id)
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
            name = arguments_dict.get('name')
            if is_success:
                summarizer(user_profile)
                return f"✏️{name} - Updated"
    return None

def delete_row(sheet_id, row_id, page_id):
    service = get_service()

    try:
        # Ensure row_id is an integer
        row_id = int(row_id)

        # Retrieve the current sheets metadata
        sheets_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()

        # Extract the sheet ID for the 'Inventory' sheet
        existing_sheets = {
            sheet['properties']['title']: sheet['properties']['sheetId']
            for sheet in sheets_metadata['sheets']
        }

        inventory_sheet_id = existing_sheets.get("Inventory")
        if inventory_sheet_id is None:
            raise ValueError("The sheet 'Inventory' does not exist in the spreadsheet.")

        # Prepare the request to delete the row
        delete_row_request = {
            "deleteDimension": {
                "range": {
                    "sheetId": inventory_sheet_id,
                    "dimension": "ROWS",
                    "startIndex": row_id - 1,
                    "endIndex": row_id,  # Google Sheets uses exclusive end index
                }
            }
        }

        # Execute the request
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [delete_row_request]}
        ).execute()

        delete_cache(page_id, cache_type)
        return True

    except Exception as e:
        print(f"Error deleting row: {e}")
        return False

def add_row(sheet_id, arguments_dict, page_id):
    product_code = arguments_dict.get('product_code', "")
    name = arguments_dict.get('name', "")
    stocks = arguments_dict.get('stocks', 0)
    price = arguments_dict.get('price', "")
    description = arguments_dict.get('description', "")
    service = get_service()

    try:
        # Extract the new row data to be appended
        new_row = [
            [product_code, name, stocks, price, description]
        ]
        
        # Use the values.append() method to append the new row at the end
        response = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Inventory",  # The range where we want to append the data (automatically adds to the end)
            valueInputOption="USER_ENTERED",  # This will allow for formatting and conversion of values (like numbers)
            body={
                "values": new_row
            }
        ).execute()

        print("Row added successfully.")
        delete_cache(page_id, cache_type)
        return True

    except Exception as e:
        print(f"Error adding row: {e}")
        return False

def edit_row(sheet_id, arguments_dict, page_id):
    row_number = arguments_dict.get('row_number') 
    product_code = arguments_dict.get('product_code', None)
    name = arguments_dict.get('name', None)
    stocks = arguments_dict.get('stocks', None)
    price = arguments_dict.get('price', None)
    description = arguments_dict.get('description', None)
    
    # Ensure row_number is provided and is a valid integer
    if row_number is None:
        print("Error: row_number is required.")
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
        current_row = result.get('values', [[]])[0]  # Get the current row, or empty list if not found

        # Prepare the new row data to be updated
        updated_values = [
            product_code if product_code is not None else current_row[0],
            name if name is not None else current_row[1],
            stocks if stocks is not None else current_row[2],
            price if price is not None else current_row[3],
            description if description is not None else current_row[4]
        ]

        # Prepare the request body for the update
        update_request = {
            "range": f"Inventory!A{row_index + 1}:E{row_index + 1}",  # The range to update (adjusts based on row number)
            "valueInputOption": "USER_ENTERED",  # Allow for user-entered values and formatting
            "values": [updated_values]  # The updated values for that row
        }

        # Update the row in the spreadsheet
        response = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"Inventory!A{row_index + 1}:E{row_index + 1}",
            valueInputOption="USER_ENTERED",
            body={"values": [updated_values]}
        ).execute()

        print(f"Row {row_number} updated successfully.")
        delete_cache(page_id, cache_type)
        return True

    except Exception as e:
        print(f"Error editing row: {e}")
        return False
