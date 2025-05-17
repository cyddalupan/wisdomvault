import json
import time
from datetime import date
import datetime

from chat.cache import delete_cache, get_cache, update_cache
from chat.service import get_service
from chat.utils import summarizer

cache_type = "inventory_admin"

def instruction(facebook_page_instance, target_row=None):
    # Check if the cached data is older than 20 seconds
    current_time = time.time()
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
        
    sales_summary = facebook_page_instance.sales
    
    return (
        "Manage users inventory. "
        "IMPORTANT: The Google Sheet is the sole source of truth regarding inventory data. "
        f"Use the 'create_sale' function to process transactions. Before completing the sale, confirm the details: "
        f"Here are the items stored on Google Sheets:\n{cached_data['data']}\n\n "
        "IMPORTANT: You are talking to the user which is the business owner, The user(owner) is selling and not buying and we will record what user sells. "
        f"Please review the products and total cost, and confirm if you'd like to proceed with the sale."
        "Do not sell if stocks is not enough."
        f"Summary of recent transactions: {sales_summary}"
    )

def generate_tools():
    tools = []

    tools.append({
        "type": "function",
        "function": {
            "name": "delete_row",
            "description": "delete one inventory item from SpreadSheet",
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
            "description": "add one inventory item, unique data from SpreadSheet",
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
            "description": "edit or update one inventory item from SpreadSheet",
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
                        "description": "stock adjustment meaning 1 to add 1 stock and negative 1 to minus 1",
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
                "required": ["name"],
            },
        }
    })

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
        
        if function_name == "create_sale":
            remarks =  arguments_dict.get('remarks', '')
            is_success = create_sale(facebook_page_instance.sheet_id, arguments_dict, remarks, True)
            if is_success:
                summarizer(user_profile)
                return "📃Order Has been created!"
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

        delete_cache(page_id, cache_type)
        return True

    except Exception as e:
        print(f"Error adding rows: {e}")
        return False

def edit_row(sheet_id, arguments_dict, page_id):
    name = arguments_dict.get('name')
    product_code = arguments_dict.get('product_code', None)
    stocks = arguments_dict.get('stocks', None)
    price = arguments_dict.get('price', None)
    description = arguments_dict.get('description', None)
    
    # Ensure name is provided
    if not name:
        return False

    service = get_service()

    try:
        today = date.today().isoformat()
        log_entries = []

        # Define helper to log changes
        def log_change(column, value):
            if value is not None:
                log_entries.append([today, name, column, value])
        
        # Log changes for each field
        log_change("Product Code", product_code)
        log_change("Stocks", stocks)
        log_change("Price", price)
        log_change("Description", description)
        
        # Append the change logs to Inventory_Logs
        if log_entries:
            service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range="Inventory_Logs",
                valueInputOption="USER_ENTERED",
                body={"values": log_entries}
            ).execute()

        delete_cache(page_id, cache_type)
        return True

    except Exception as e:
        print(f"Error logging change: {e}")
        return False

def create_sale(sheet_id, arguments_dict, remarks, is_approve):
    print("create_sale dict", arguments_dict)
    service = get_service()

    sales_data = []
    sale_time = datetime.date.today().isoformat()  # Use today's date

    for item in arguments_dict.get('items', []):
        name = item.get('name')
        quantity = item.get('quantity')

        # Prepare data for Sales_Logs sheet
        sales_data.append([is_approve, sale_time, name, quantity, remarks])

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
