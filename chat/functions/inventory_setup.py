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

        # Add sheets if they do not exist
        if "Dashboard" not in existing_sheets:
            requests.append(add_sheet_request("Dashboard"))
        if "Inventory" not in existing_sheets:
            requests.append(add_sheet_request("Inventory"))
        if "Sales" not in existing_sheets:
            requests.append(add_sheet_request("Sales"))
        if "Sales Summary" not in existing_sheets:
            requests.append(add_sheet_request("Sales Summary"))

        # Perform batch update to add missing sheets
        if requests:
            service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()

        # Retrieve sheet IDs for all necessary sheets
        sheets_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        dashboard_sheet_id = existing_sheets.get("Dashboard", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Dashboard"))
        inventory_sheet_id = existing_sheets.get("Inventory", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Inventory"))
        sales_sheet_id = existing_sheets.get("Sales", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Sales"))
        sales_summary_sheet_id = existing_sheets.get("Sales Summary", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Sales Summary"))

        # Reorder sheets and format them
        reorder_sheets(service, sheet_id, dashboard_sheet_id, inventory_sheet_id, sales_summary_sheet_id, sales_sheet_id)
        format_inventory_sheet(service, sheet_id, inventory_sheet_id)
        format_sales_sheet(service, sheet_id, sales_sheet_id)
        format_sales_summary_sheet(service, sheet_id, sales_summary_sheet_id)
        format_dashboard_sheet(service, sheet_id, dashboard_sheet_id, inventory_sheet_id, sales_summary_sheet_id, sales_sheet_id)

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

def reorder_sheets(service, sheet_id, dashboard_sheet_id, inventory_sheet_id, sales_summary_sheet_id, sales_sheet_id):
    reorder_request = [
        {"updateSheetProperties": {"properties": {"sheetId": dashboard_sheet_id, "index": 0}, "fields": "index"}},
        {"updateSheetProperties": {"properties": {"sheetId": inventory_sheet_id, "index": 1}, "fields": "index"}},
        {"updateSheetProperties": {"properties": {"sheetId": sales_summary_sheet_id, "index": 2}, "fields": "index"}},
        {"updateSheetProperties": {"properties": {"sheetId": sales_sheet_id, "index": 3}, "fields": "index"}}
    ]
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": reorder_request}).execute()

def format_inventory_sheet(service, sheet_id, inventory_sheet_id):
    # Formatting definitions
    def create_format(bg_color=None, text_color=None, bold=False, font_size=12, align="CENTER"):
        format_dict = {
            "textFormat": {"bold": bold, "fontFamily": "Arial", "fontSize": font_size},
            "horizontalAlignment": align
        }
        if bg_color:
            format_dict["backgroundColor"] = bg_color
        if text_color:
            format_dict["textFormat"]["foregroundColor"] = text_color
        return format_dict

    # Header format (black background with white text)
    header_format = create_format(
        bg_color={"red": 0, "green": 0, "blue": 0},  # Black
        text_color={"red": 1, "green": 1, "blue": 1},  # White
        bold=True
    )

    # Only keep specific columns (you can adjust the columns here)
    headers = ["Product Code", "Name", "Stocks", "Price", "Description"]  # Removed "Price" and "Description"

    # Requests for header formatting
    format_header_request = {
        "updateCells": {
            "rows": [{
                "values": [
                    {"userEnteredValue": {"stringValue": header}, "userEnteredFormat": header_format}
                    for header in headers
                ]
            }],
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": inventory_sheet_id, "rowIndex": 0, "columnIndex": 0},
        }
    }

    # Resize columns request
    resize_columns_request = {
        "updateDimensionProperties": {
            "range": {"sheetId": inventory_sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": len(headers)},
            "properties": {"pixelSize": 150},
            "fields": "pixelSize",
        }
    }

    # Sample data for the sheet
    sample_data = [
        ["12345", "🛒 Product A", 100, 10.00, "A great product"],
        ["67890", "🔥 Product B", 5, 25.00, "A popular item"],
        ["11223", "🍏 Product C", 0, 7.50, "Out of stock"],
        ["44556", "📦 Product D", 60, 12.00, "Regular stock"],
        ["99887", "💎 Product E", 15, 100.00, "Limited edition"],
    ]

    # Generate requests for sample data
    data_requests = [
        {
            "values": [
                {"userEnteredValue": {("numberValue" if isinstance(val, (int, float)) else "stringValue"): val}}
                for val in row
            ]
        } for row in sample_data
    ]

    populate_sample_data_request = {
        "updateCells": {
            "rows": data_requests,
            "fields": "userEnteredValue",
            "start": {"sheetId": inventory_sheet_id, "rowIndex": 1, "columnIndex": 0},
        }
    }

    # Batch update request
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [format_header_request, resize_columns_request, populate_sample_data_request]}
    ).execute()

    return True

def format_dashboard_sheet(service, sheet_id, dashboard_sheet_id, inventory_sheet_id, sales_summary_sheet_id, sales_sheet_id):
    try:
        # Chart 1: Inventory Stock Levels (Column Chart)
        add_stock_chart_request = {
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
                                                    "startRowIndex": 1,
                                                    "startColumnIndex": 1,
                                                    "endColumnIndex": 2,
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
                                                    "startRowIndex": 1,
                                                    "startColumnIndex": 2,
                                                    "endColumnIndex": 3,
                                                }
                                            ]
                                        }
                                    },
                                    "color": {
                                        "red": 0,
                                        "green": 0,
                                        "blue": 0
                                    }
                                }
                            ],
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

        # Chart 2: Sales Summary (Smooth Line Chart)
        add_sales_summary_chart_request = {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Sales Over Time",
                        "basicChart": {
                            "chartType": "LINE",
                            "legendPosition": "BOTTOM_LEGEND",
                            "lineSmoothing": True,
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Date Time"},
                                {"position": "LEFT_AXIS", "title": "Sale Total"},
                            ],
                            "domains": [
                                {
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": sales_summary_sheet_id,
                                                    "startRowIndex": 1,
                                                    "startColumnIndex": 0,
                                                    "endColumnIndex": 1,
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
                                                    "sheetId": sales_summary_sheet_id,
                                                    "startRowIndex": 1,
                                                    "startColumnIndex": 1,
                                                    "endColumnIndex": 2,
                                                }
                                            ]
                                        }
                                    },
                                    "color": {
                                        "red": 0,
                                        "green": 0,
                                        "blue": 0
                                    }
                                }
                            ],
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": dashboard_sheet_id, "rowIndex": 0, "columnIndex": 6}  # Example coordinates
                        }
                    }
                }
            }
        }

        # Chart 3: Best Selling Products (Bar Chart)
        add_best_selling_chart_request = {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Best Selling Products",
                        "basicChart": {
                            "chartType": "COLUMN",
                            "legendPosition": "BOTTOM_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Product Names"},
                                {"position": "LEFT_AXIS", "title": "Quantity Sold"},
                            ],
                            "domains": [
                                {
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": sales_sheet_id,
                                                    "startRowIndex": 1,
                                                    "startColumnIndex": 1,
                                                    "endColumnIndex": 2,
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
                                                    "sheetId": sales_sheet_id,
                                                    "startRowIndex": 1,
                                                    "startColumnIndex": 2,
                                                    "endColumnIndex": 3,
                                                }
                                            ]
                                        }
                                    },
                                    "color": {
                                        "red": 0,
                                        "green": 0,
                                        "blue": 0
                                    }
                                }
                            ],
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": dashboard_sheet_id, "rowIndex": 19, "columnIndex": 0}
                        }
                    },
                }
            }
        }

        # Add the charts to the dashboard
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [
                add_stock_chart_request,
                add_sales_summary_chart_request,
                add_best_selling_chart_request
            ]}
        ).execute()

        print("Charts added successfully:", response)

    except HttpError as err:
        print(f"Error while adding the charts: {err}")

def format_sales_sheet(service, sheet_id, sales_sheet_id):
    def header_format():
        return {
            "backgroundColor": {"red": 0, "green": 0, "blue": 0},  # Dark teal
            "textFormat": {"bold": True, "fontFamily": "Arial", "fontSize": 12, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER"
        }

    def currency_format():
        return {
            "numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"}
        }

    def number_format():
        return {
            "numberFormat": {"type": "NUMBER", "pattern": "#,##0"}
        }

    # Define the header formatting
    format_header_request = {
        "updateCells": {
            "rows": [{
                "values": [
                    {"userEnteredValue": {"stringValue": "Date Time"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Product Name"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Quantity"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Total Amount"}, "userEnteredFormat": header_format()},
                ]
            }],
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": sales_sheet_id, "rowIndex": 0, "columnIndex": 0},
        }
    }

    # Resize columns
    resize_columns_request = {
        "updateDimensionProperties": {
            "range": {"sheetId": sales_sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 4},
            "properties": {"pixelSize": 150},
            "fields": "pixelSize",
        }
    }

    # Add test data
    test_data = [
        ["2025-01-04 10:30:00", "Product A", 2, 20.00],
        ["2025-01-04 11:00:00", "Product B", 5, 50.00],
        ["2025-01-04 11:30:00", "Product C", 1, 15.00],
        ["2025-01-04 12:34:00", "Product A", 5, 50.00],
        ["2025-01-04 12:34:00", "Product B", 15, 300.00],
        ["2025-01-04 12:34:00", "Product C", 12, 310.00],
    ]

    test_data_requests = []
    for i, row in enumerate(test_data):
        values = []
        for j, val in enumerate(row):
            cell_format = {}
            if j == 2:  # Quantity column
                cell_format = number_format()
            elif j == 3:  # Total Amount column
                cell_format = currency_format()

            values.append({"userEnteredValue": {"numberValue" if isinstance(val, (int, float)) else "stringValue": val}, 
                           "userEnteredFormat": cell_format})
        test_data_requests.append({"values": values})

    add_test_data_request = {
        "updateCells": {
            "rows": test_data_requests,
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": sales_sheet_id, "rowIndex": 1, "columnIndex": 0},
        }
    }

    # Apply all the updates to the sheet
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [format_header_request, resize_columns_request, add_test_data_request]}
    ).execute()

    return True

def format_sales_summary_sheet(service, sheet_id, sales_summary_sheet_id):
    def header_format():
        return {
            "backgroundColor": {"red": 0, "green": 0, "blue": 0},  # Dark teal
            "textFormat": {"bold": True, "fontFamily": "Arial", "fontSize": 12, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER"
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
                    {"userEnteredValue": {"stringValue": "Date Time"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Sale Total"}, "userEnteredFormat": header_format()},
                ]
            }],
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": sales_summary_sheet_id, "rowIndex": 0, "columnIndex": 0},
        }
    }

    # Resize columns
    resize_columns_request = {
        "updateDimensionProperties": {
            "range": {"sheetId": sales_summary_sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 2},
            "properties": {"pixelSize": 200},
            "fields": "pixelSize",
        }
    }

    # Test data aggregated by date-time
    summary_test_data = [
        ["2025-01-04 10:30:00", 20.00],
        ["2025-01-04 11:00:00", 50.00],
        ["2025-01-04 11:30:00", 15.00],
        ["2025-01-04 12:34:00", 660.00],  # Combined totals for this timestamp
    ]

    test_data_requests = []
    for row in summary_test_data:
        values = [
            {"userEnteredValue": {"stringValue": row[0]}},  # Date Time
            {"userEnteredValue": {"numberValue": row[1]}, "userEnteredFormat": currency_format()},  # Sale Total
        ]
        test_data_requests.append({"values": values})

    add_test_data_request = {
        "updateCells": {
            "rows": test_data_requests,
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": sales_summary_sheet_id, "rowIndex": 1, "columnIndex": 0},
        }
    }

    # Apply all the updates to the sheet
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [format_header_request, resize_columns_request, add_test_data_request]}
    ).execute()

    return True
