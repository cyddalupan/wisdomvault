import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account


def instruction(facebook_page_instance):
    return "setting up the inventory sheets"

def generate_tools():
    tools = []

    tools.append({
        "type": "function",
        "function": {
            "name": "generate_sheet",
            "description": "initialize the sheets format",
            "parameters": {
                "type": "object",
                "properties": {
                    "agree": {
                        "type": "boolean",
                        "description": "users agree to initialize the spreadsheet format",
                    },
                },
                "required": ["agree"],
            },
        }
    })

    return tools

def tool_function(tool_calls, user_profile, facebook_page_instance):
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments
        arguments_dict = json.loads(arguments)

        if function_name == "generate_sheet":
            agree = arguments_dict.get('agree', False)
            if agree:
                is_success = format_sheets(facebook_page_instance.sheet_id)
                if is_success:
                    user_profile.task = "inventory"
                    user_profile.save()
                    return "I am now done formatting your sheet. Do you want to start adding Items?"
    return None

def get_service():
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def format_sheets(sheet_id):
    service = get_service()

    try:
        # Retrieve the current sheets metadata
        sheets_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        existing_sheets = {sheet['properties']['title']: sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets']}

        requests = []

        # Add Dashboard and Inventory sheets if not exist
        if "Dashboard" not in existing_sheets:
            requests.append(add_sheet_request("Dashboard"))
        if "Inventory" not in existing_sheets:
            requests.append(add_sheet_request("Inventory"))

        # Perform batch update to add missing sheets
        if requests:
            service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()

        # Retrieve sheetId for Dashboard and Inventory after update
        sheets_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        dashboard_sheet_id = existing_sheets.get("Dashboard", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Dashboard"))
        inventory_sheet_id = existing_sheets.get("Inventory", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Inventory"))

        # Reorder sheets: Dashboard first, Inventory second
        reorder_sheets(service, sheet_id, dashboard_sheet_id, inventory_sheet_id)

        # Format Inventory and Dashboard sheets
        format_inventory_sheet(service, sheet_id, inventory_sheet_id)
        format_dashboard_sheet(service, sheet_id, dashboard_sheet_id, inventory_sheet_id)

        return "Sheets formatted successfully!"

    except HttpError as err:
        return f"An error occurred: {err}"

def add_sheet_request(sheet_title):
    return {
        "addSheet": {
            "properties": {
                "title": sheet_title,
            }
        }
    }

def reorder_sheets(service, sheet_id, dashboard_sheet_id, inventory_sheet_id):
    reorder_request = [
        {"updateSheetProperties": {"properties": {"sheetId": dashboard_sheet_id, "index": 0}, "fields": "index"}},
        {"updateSheetProperties": {"properties": {"sheetId": inventory_sheet_id, "index": 1}, "fields": "index"}}
    ]
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": reorder_request}).execute()

def format_inventory_sheet(service, sheet_id, inventory_sheet_id):
    def header_format():
        return {
            "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.6},  # Dark teal
            "textFormat": {"bold": True, "fontFamily": "Arial", "fontSize": 12, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER"
        }

    def row_alternation_format():
        return {
            "backgroundColor": {"red": 0.9, "green": 0.96, "blue": 0.96},  # Light teal
        }

    def stock_alert_format(stock):
        if stock <= 10:
            return {"backgroundColor": {"red": 1, "green": 0.8, "blue": 0.8}, "textFormat": {"bold": True}}  # Red
        elif stock <= 50:
            return {"backgroundColor": {"red": 1, "green": 1, "blue": 0.6}}  # Yellow
        else:
            return {"backgroundColor": {"red": 0.8, "green": 1, "blue": 0.8}}  # Green

    def number_format():
        return {
            "numberFormat": {"type": "NUMBER", "pattern": "#,##0"}
        }

    def currency_format():
        return {
            "numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"}
        }

    # Define the header formatting
    format_header_request = {
        "updateCells": {
            "rows": [{
                "values": [
                    {"userEnteredValue": {"stringValue": "Product Code"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Name"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Stocks"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Price"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Description"}, "userEnteredFormat": header_format()},
                ]
            }],
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": inventory_sheet_id, "rowIndex": 0, "columnIndex": 0},
        }
    }

    # Resize columns
    resize_columns_request = {
        "updateDimensionProperties": {
            "range": {"sheetId": inventory_sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 5},
            "properties": {"pixelSize": 150},
            "fields": "pixelSize",
        }
    }

    # Add sample default values for inventory
    sample_data = [
        ["12345", "🛒 Product A", 100, 10.00, "A great product"],
        ["67890", "🔥 Product B", 5, 25.00, "A popular item"],
        ["11223", "🍏 Product C", 0, 7.50, "Out of stock"],
        ["44556", "📦 Product D", 60, 12.00, "Regular stock"],
        ["99887", "💎 Product E", 15, 100.00, "Limited edition"],
    ]

    # Prepare requests for sample data
    data_requests = []
    for i, row in enumerate(sample_data):
        values = []
        for j, val in enumerate(row):
            cell_format = {}
            if j == 2:  # Stocks column
                cell_format = {**stock_alert_format(val), **number_format()} if isinstance(val, int) else {}
            elif j == 3:  # Price column
                cell_format = currency_format()
            elif i % 2 == 0:  # Alternate row styling
                cell_format = row_alternation_format()

            values.append({"userEnteredValue": {"numberValue" if isinstance(val, (int, float)) else "stringValue": val}, "userEnteredFormat": cell_format})
        data_requests.append({"values": values})

    populate_sample_data_request = {
        "updateCells": {
            "rows": data_requests,
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": inventory_sheet_id, "rowIndex": 1, "columnIndex": 0},
        }
    }

    # Apply all the updates to the sheet
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [format_header_request, resize_columns_request, populate_sample_data_request]}
    ).execute()

    return True

def format_dashboard_sheet(service, sheet_id, dashboard_sheet_id, inventory_sheet_id):
    try:
        # Define the chart request with valid position
        add_chart_request = {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Stock Levels",
                        "basicChart": {
                            "chartType": "COLUMN",
                            "legendPosition": "BOTTOM_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Item Names"},
                                {"position": "LEFT_AXIS", "title": "Stock Count"},
                            ],
                            "domains": [
                                {
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": inventory_sheet_id,
                                                    "startRowIndex": 1,  # Data starts after header
                                                    "startColumnIndex": 1,  # "Name" column
                                                    "endColumnIndex": 2,  # Just one column
                                                }
                                            ]
                                        }
                                    }
                                }
                            ],
                            "series": [
                                {
                                    "series": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": inventory_sheet_id,
                                                    "startRowIndex": 1,  # Data starts after header
                                                    "startColumnIndex": 2,  # "Stocks" column
                                                    "endColumnIndex": 3,  # Just one column
                                                }
                                            ]
                                        }
                                    }
                                }
                            ],
                        }
                    },
                    "position": {  # Use overlayPosition without conflicts
                        "overlayPosition": {
                            "anchorCell": {"sheetId": dashboard_sheet_id, "rowIndex": 0, "columnIndex": 0}
                        }
                    },
                }
            }
        }

        # Add the chart to the dashboard
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id, body={"requests": [add_chart_request]}
        ).execute()

        print("Chart added successfully:", response)

    except HttpError as err:
        print(f"Error while adding the chart: {err}")
