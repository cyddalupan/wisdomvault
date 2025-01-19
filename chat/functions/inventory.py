import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import time

from chat.utils import summarizer

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

    return f"Manage users' inventory stored on Google Sheets:\n{cached_data['data']}"

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
                },
                "required": ["row_number", "confirmation"],
            },
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "add_row",
            "description": "add one row from SpreadSheet",
            "parameters": {
                "type": "object",
                "properties": {
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
                    "desciprtion": {
                        "type": "string",
                        "description": "product description",
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
            confirmation = arguments_dict.get('confirmation', False)
            if confirmation and row_number:
                is_success = delete_row(facebook_page_instance.sheet_id, row_number)
                if is_success:
                    summarizer(user_profile)
                    return "✅"
        
        if function_name == "add_row":
            is_success = add_row(facebook_page_instance.sheet_id, arguments_dict)
            if is_success:
                summarizer(user_profile)
                return "✅"
        
        if function_name == "edit_row":
            is_success = edit_row(facebook_page_instance.sheet_id, arguments_dict)
            if is_success:
                summarizer(user_profile)
                return "✅"
    return None

def get_service():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def clear_cached_data():
    global cached_data
    cached_data = {
        'data': None,
        'timestamp': 0
    }

def delete_row(sheet_id, row_id):
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

        clear_cached_data()
        return True

    except Exception as e:
        print(f"Error deleting row: {e}")
        return False

def add_row(sheet_id, arguments_dict):
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
        clear_cached_data()
        return True

    except Exception as e:
        print(f"Error adding row: {e}")
        return False

def edit_row(sheet_id, arguments_dict):
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
        clear_cached_data()
        return True

    except Exception as e:
        print(f"Error editing row: {e}")
        return False
