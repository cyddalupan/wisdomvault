import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account


def instruction():
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

    # Save updated user profile in Django without errors
    user_profile.task = ""
    user_profile.save()
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
        format_dashboard_sheet(service, sheet_id, dashboard_sheet_id)

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
            "backgroundColor": {"red": 0.8, "green": 0.9, "blue": 1},
            "textFormat": {"bold": True},
            "horizontalAlignment": "CENTER"
        }

    format_request = {
        "updateCells": {
            "rows": [{
                "values": [
                    {"userEnteredValue": {"stringValue": "Product Code"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Stocks"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Name"}, "userEnteredFormat": header_format()},
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

    # Apply formatting to the Inventory sheet
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": [format_request, resize_columns_request]}).execute()

def format_dashboard_sheet(service, sheet_id, dashboard_sheet_id):
    # Add a graph to the Dashboard sheet
    add_chart_request = {
        "addChart": {
            "chart": {
                "spec": {
                    "title": "Stock Levels",
                    "basicChart": {
                        "chartType": "COLUMN",
                        "legendPosition": "BOTTOM_LEGEND",
                        "axis": [
                            {"position": "BOTTOM_AXIS", "title": "Items"},
                            {"position": "LEFT_AXIS", "title": "Stock Count"},
                        ],
                        "domains": [
                            {"domain": {"sourceRange": {"sources": [{"sheetId": dashboard_sheet_id, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 1}]}}}
                        ],
                        "series": [
                            {"series": {"sourceRange": {"sources": [{"sheetId": dashboard_sheet_id, "startRowIndex": 1, "startColumnIndex": 1, "endColumnIndex": 2}]}}}
                        ]
                    }
                },
                "position": {
                    "overlayPosition": {
                        "anchorCell": {"sheetId": dashboard_sheet_id, "rowIndex": 0, "columnIndex": 0}
                    }
                },
            }
        }
    }

    # Add the chart to the dashboard
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": [add_chart_request]}).execute()
