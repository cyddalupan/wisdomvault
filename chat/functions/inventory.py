import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

def instruction(facebook_page_instance, target_row=None):
    # TODO find a way to store value for 1minute
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
                inventory_message = "Current Inventory Data:\n"
                for i, row in enumerate(values):
                    row_info = f"Row {i + 1}: {', '.join(row)}"
                    if target_row is not None and i == target_row:
                        row_info += " <-- Target Row"
                    inventory_message += row_info + "\n"

            return f"Manage users' inventory stored on Google Sheets:\n{inventory_message}"

        except Exception as e:
            return f"Error fetching inventory data: {e}"

    return "Manage users' inventory that is on Google Sheets."

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
    return None

def get_service():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def delete_row(sheet_id, row_id):
    """
    Deletes a row in a Google Sheet by its row index.

    Args:
        sheet_id (str): The ID of the Google Sheet.
        row_id (str | int): The zero-based index of the row to delete.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    print(f"Starting delete_row with sheet_id={sheet_id} and row_id={row_id}")
    service = get_service()

    try:
        # Ensure row_id is an integer
        row_id = int(row_id)
        print(f"Converted row_id to integer: {row_id}")

        # Retrieve the current sheets metadata
        print("Fetching sheets metadata...")
        sheets_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        print(f"Retrieved sheets metadata: {sheets_metadata}")

        # Extract the sheet ID for the 'Inventory' sheet
        existing_sheets = {
            sheet['properties']['title']: sheet['properties']['sheetId']
            for sheet in sheets_metadata['sheets']
        }
        print(f"Existing sheets found: {existing_sheets}")

        inventory_sheet_id = existing_sheets.get("Inventory")
        if inventory_sheet_id is None:
            print("Error: The sheet 'Inventory' does not exist.")
            raise ValueError("The sheet 'Inventory' does not exist in the spreadsheet.")
        print(f"Inventory sheet ID: {inventory_sheet_id}")

        # Prepare the request to delete the row
        delete_row_request = {
            "deleteDimension": {
                "range": {
                    "sheetId": inventory_sheet_id,
                    "dimension": "ROWS",
                    "startIndex": row_id,
                    "endIndex": row_id + 1,  # Google Sheets uses exclusive end index
                }
            }
        }
        print(f"Delete row request prepared: {delete_row_request}")

        # Execute the request
        print("Sending batchUpdate request...")
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [delete_row_request]}
        ).execute()
        print(f"Batch update response: {response}")

        print("Row deleted successfully.")
        return True

    except Exception as e:
        print(f"Error deleting row: {e}")
        return False
