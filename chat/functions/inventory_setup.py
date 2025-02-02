import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

from chat.utils import get_service


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
        if "Leads" not in existing_sheets:
            requests.append(add_sheet_request("Leads"))

        # Perform batch update to add missing sheets
        if requests:
            service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()

        # Retrieve sheet IDs for all necessary sheets
        sheets_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        dashboard_sheet_id = existing_sheets.get("Dashboard", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Dashboard"))
        inventory_sheet_id = existing_sheets.get("Inventory", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Inventory"))
        sales_sheet_id = existing_sheets.get("Sales", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Sales"))
        sales_summary_sheet_id = existing_sheets.get("Sales Summary", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Sales Summary"))
        leads_sheet_id = existing_sheets.get("Leads", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Leads"))
        
        # Reorder sheets and format them
        reorder_sheets(service, sheet_id, dashboard_sheet_id, inventory_sheet_id, sales_summary_sheet_id, sales_sheet_id)
        format_inventory_sheet(service, sheet_id, inventory_sheet_id)
        format_leads_sheet(service, sheet_id, leads_sheet_id)
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
                                }
                            ],
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {"sheetId": dashboard_sheet_id, "rowIndex": 18, "columnIndex": 0}
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
            "numberFormat": {"type": "CURRENCY", "pattern": "#,##0.00"}
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
            "numberFormat": {"type": "CURRENCY", "pattern": "#,##0.00"}
        }

    # Define the header formatting
    format_header_request = {
        "updateCells": {
            "rows": [{
                "values": [
                    {"userEnteredValue": {"stringValue": "Date Time"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Sale Total"}, "userEnteredFormat": header_format()},
                    {"userEnteredValue": {"stringValue": "Customer"}, "userEnteredFormat": header_format()},
                ]
            }],
            "fields": "userEnteredValue,userEnteredFormat,userEnteredValue",
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
        ["2025-01-04 10:30:00", 20.00, "Mark"],
        ["2025-01-04 11:00:00", 50.00, ""],
        ["2025-01-04 11:30:00", 15.00, ""],
        ["2025-01-04 12:34:00", 660.00, "Andrew"],  # Combined totals for this timestamp
    ]

    test_data_requests = []
    for row in summary_test_data:
        values = [
            {"userEnteredValue": {"stringValue": row[0]}},  # Date Time
            {"userEnteredValue": {"numberValue": row[1]}, "userEnteredFormat": currency_format()},  # Sale Total
            {"userEnteredValue": {"stringValue": row[2]}},
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

def format_leads_sheet(service, sheet_id, leads_sheet_id):
    # Formatting definitions
    def create_format(bg_color=None, text_color=None, bold=False, font_size=12, align="CENTER", border=None):
        format_dict = {
            "textFormat": {"bold": bold, "fontFamily": "Arial", "fontSize": font_size},
            "horizontalAlignment": align
        }
        if bg_color:
            format_dict["backgroundColor"] = bg_color
        if text_color:
            format_dict["textFormat"]["foregroundColor"] = text_color
        if border:
            format_dict["borders"] = border
        return format_dict

    # Header format for "User Leads"
    user_leads_format = create_format(
        bg_color={"red": 0.615, "green": 0.764, "blue": 0.902},  # #9dc3e6
        text_color={"red": 0.067, "green": 0.067, "blue": 0.067},  # #111111
        bold=True,  # Set to bold
        font_size=21
    )

    # Create the request for merging cells A1 to G1
    merge_cells_request = {
        "mergeCells": {
            "range": {
                "sheetId": leads_sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": 7
            },
            "mergeType": "MERGE_ALL"
        }
    }

    # Request to set the "User Leads" header
    user_leads_header_request = {
        "updateCells": {
            "rows": [{
                "values": [
                    {"userEnteredValue": {"stringValue": "User Leads"}, "userEnteredFormat": user_leads_format}
                ]
            }],
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": leads_sheet_id, "rowIndex": 0, "columnIndex": 0},
        }
    }

    # Set height of the first row to double
    row_height_request = {
        "updateDimensionProperties": {
            "range": {
                "sheetId": leads_sheet_id,
                "dimension": "ROWS",
                "startIndex": 0,
                "endIndex": 1,
            },
            "properties": {
                "pixelSize": 40  # Assuming original height is 20, thus double it
            },
            "fields": "pixelSize"
        }
    }

    # Add a black row under the header
    black_row_format = create_format(bg_color={"red": 0, "green": 0, "blue": 0})  # Black background

    black_row_request = {
        "updateCells": {
            "rows": [{
                "values": [
                    {"userEnteredValue": {"stringValue": ""}, "userEnteredFormat": black_row_format} 
                    for _ in range(7)  # Filling A2 to G2
                ]
            }],
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": leads_sheet_id, "rowIndex": 1, "columnIndex": 0},
        }
    }

    # Header format for the leads sheet with border
    leads_header_format = create_format(
        bg_color={"red": 0.611, "green": 0.765, "blue": 0.890},  # #9cc2e5
        text_color={"red": 0.067, "green": 0.067, "blue": 0.067},  # #111111
        bold=True,
        font_size=10,
        border={
            "top": {"style": "SOLID", "width": 2, "color": {"red": 1, "green": 1, "blue": 1}},
            "bottom": {"style": "SOLID", "width": 2, "color": {"red": 1, "green": 1, "blue": 1}},
            "left": {"style": "SOLID", "width": 2, "color": {"red": 1, "green": 1, "blue": 1}},
            "right": {"style": "SOLID", "width": 2, "color": {"red": 1, "green": 1, "blue": 1}},
        }
    )

    # Headers for the leads sheet
    headers = ["Name", "Mobile", "Gender", "Age", "Address", "Birthday", "Status"]

    # Requests for header formatting (using two rows for each header)
    header_requests = []
    for header in headers:
        merged_cells_request = {
            "mergeCells": {
                "range": {
                    "sheetId": leads_sheet_id,
                    "startRowIndex": 2,
                    "endRowIndex": 4,
                    "startColumnIndex": headers.index(header),
                    "endColumnIndex": headers.index(header) + 1
                },
                "mergeType": "MERGE_ALL"
            }
        }
        header_requests.append(merged_cells_request)

        header_row_request = {
            "updateCells": {
                "rows": [{
                    "values": [
                        {"userEnteredValue": {"stringValue": header}, "userEnteredFormat": leads_header_format}
                    ]
                }],
                "fields": "userEnteredValue,userEnteredFormat",
                "start": {"sheetId": leads_sheet_id, "rowIndex": 2, "columnIndex": headers.index(header)},
            }
        }
        header_requests.append(header_row_request)

    # Resize columns request
    resize_columns_request = {
        "updateDimensionProperties": {
            "range": {"sheetId": leads_sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": len(headers)},
            "properties": {"pixelSize": 150},
            "fields": "pixelSize",
        }
    }

    # Sample data for the sheet
    sample_data = [
        ["John Doe", "1234567890", "Male", 30, "123 Main St, Anytown", "1993-05-15", "Active"],
        ["Jane Smith", "0987654321", "Female", 25, "456 Elm St, Othertown", "1998-08-22", "Inactive"],
        ["Sam Wilson", "1112223333", "Male", 45, "789 Oak St, Sometown", "1978-11-30", "Active"],
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
            "start": {"sheetId": leads_sheet_id, "rowIndex": 4, "columnIndex": 0},  # Adjusted to row 4 for data
        }
    }

    # Request to remove gridlines
    remove_gridlines_request = {
        "updateSheetProperties": {
            "properties": {
                "sheetId": leads_sheet_id,
                "gridProperties": {
                    "hideGridlines": True
                }
            },
            "fields": "gridProperties.hideGridlines"
        }
    }

    # Batch update request
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [
            merge_cells_request,
            user_leads_header_request,
            row_height_request,  # Set row height
            black_row_request,
            *header_requests,  # Unpack header requests
            resize_columns_request,
            populate_sample_data_request,
            remove_gridlines_request
        ]}
    ).execute()

    return True