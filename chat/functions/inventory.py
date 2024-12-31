import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import time

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
                    return "Row Deleted. What else can I help you?"
        
        if function_name == "add_row":
            product_code = arguments_dict.get('product_code', "")
            name = arguments_dict.get('name', "")
            stocks = arguments_dict.get('stocks', 0)
            price = arguments_dict.get('price', "")
            desciprtion = arguments_dict.get('desciprtion', "")
            is_success = add_row(facebook_page_instance.sheet_id, product_code, name, stocks, price, desciprtion)
            if is_success:
                return "Row Add. What else can I help you?"
    return None

def get_service():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

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

        return True

    except Exception as e:
        print(f"Error deleting row: {e}")
        return False

def add_row(sheet_id, product_code, name, stocks, price, description):
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
        return True

    except Exception as e:
        print(f"Error adding row: {e}")
        return False
