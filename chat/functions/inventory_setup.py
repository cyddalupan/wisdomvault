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
        # if "Leads" not in existing_sheets:  # Check for "Leads" sheet
        #     requests.append(add_sheet_request("Leads"))

        # Perform batch update to add missing sheets
        if requests:
            service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()

        # Retrieve sheet IDs for all necessary sheets
        sheets_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        dashboard_sheet_id = existing_sheets.get("Dashboard", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Dashboard"))
        inventory_sheet_id = existing_sheets.get("Inventory", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Inventory"))
        sales_sheet_id = existing_sheets.get("Sales", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Sales"))
        sales_summary_sheet_id = existing_sheets.get("Sales Summary", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Sales Summary"))
        #leads_sheet_id = existing_sheets.get("Leads", next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == "Leads"))
        
        # Copy the "Leads" sheet from another spreadsheet (ID: 1afqON02xQARmS1GwL8Gg9XFE6lf_IPIjJXAFqrHFJKc)
        copy_leads_sheet(service, sheet_id, "1afqON02xQARmS1GwL8Gg9XFE6lf_IPIjJXAFqrHFJKc")

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

def copy_leads_sheet(service, destination_sheet_id, source_sheet_id):
    try:
        # Step 1: Fetch the data from the source "Leads" sheet
        print("Fetching data from source 'Leads' sheet...")
        response = service.spreadsheets().values().get(spreadsheetId=source_sheet_id, range="Leads").execute()
        leads_data = response.get('values', [])

        if not leads_data:
            print("No data found in the source Leads sheet.")
            return "No data found in the source Leads sheet."

        print(f"Fetched data from source: {leads_data[:5]}...")  # Show a sample of data

        # Step 2: Create the "Leads" sheet in the destination spreadsheet (if not already created)
        print("Creating 'Leads' sheet in destination spreadsheet...")
        add_sheet_request = {
            "addSheet": {
                "properties": {
                    "title": "Leads"
                }
            }
        }

        batch_update_request = {
            "requests": [add_sheet_request]
        }

        # Execute the batch update to create the "Leads" sheet
        service.spreadsheets().batchUpdate(spreadsheetId=destination_sheet_id, body=batch_update_request).execute()
        print("Leads sheet created!")

        # Step 3: Write the data from the source to the new "Leads" sheet in the destination
        print("Writing data to destination 'Leads' sheet...")
        paste_data_request = {
            "range": "Leads!A1",  # Paste starting from the first cell of the new sheet
            "values": leads_data
        }

        # Write data to the destination sheet
        service.spreadsheets().values().update(
            spreadsheetId=destination_sheet_id,
            range=paste_data_request["range"],
            valueInputOption="RAW",
            body={"values": paste_data_request["values"]}
        ).execute()

        # Step 4: Copy the formatting from the source sheet to the destination sheet
        print("Fetching formatting from source 'Leads' sheet...")
        formatting_response = service.spreadsheets().get(spreadsheetId=source_sheet_id).execute()

        # Find the source sheet by name ("Leads")
        source_sheet = next(sheet for sheet in formatting_response['sheets'] if sheet['properties']['title'] == "Leads")
        
        # Now, retrieve the sheetId and formatting info for this sheet
        source_sheet_id = source_sheet['properties']['sheetId']

        # Get the actual formatting (cell colors, text formatting) using a "get" request
        requests = []

        # Copy the entire formatting from the source sheet to the new sheet in the destination
        print("Copying formatting to destination 'Leads' sheet...")

        # This retrieves all cells' format data in the source sheet
        for row_idx, row in enumerate(source_sheet.get('data', [])):
            for col_idx, cell in enumerate(row.get('rowData', [])):
                # Format each cell based on its contents
                if 'values' in cell:
                    # Formatting cells from the source sheet to destination sheet
                    format_request = {
                        "updateCells": {
                            "range": {
                                "sheetId": source_sheet_id,  # Sheet ID of the "Leads" sheet
                                "startRowIndex": row_idx,
                                "startColumnIndex": col_idx,
                            },
                            "rows": [
                                {
                                    "values": [
                                        {"userEnteredFormat": cell["userEnteredFormat"]}
                                    ]
                                }
                            ],
                            "fields": "userEnteredFormat"  # Only copy the formatting
                        }
                    }
                    requests.append(format_request)

        # Apply the formatting
        if requests:
            service.spreadsheets().batchUpdate(spreadsheetId=destination_sheet_id, body={"requests": requests}).execute()
            print("Formatting copied successfully!")

        return "Leads sheet copied successfully with data and formatting!"

    except HttpError as err:
        print(f"Error occurred: {err}")
        return f"An error occurred: {err}"

def format_leads_sheet(service, sheet_id, source_sheet_id):
    try:
        # Fetch the data from the "Leads" sheet in the source spreadsheet
        response = service.spreadsheets().values().get(spreadsheetId=source_sheet_id, range="Leads").execute()
        leads_data = response.get('values', [])

        if not leads_data:
            return "No data found in the Leads sheet."

        # Create a new sheet called "Leads" in the destination spreadsheet
        add_sheet_request = {
            "addSheet": {
                "properties": {
                    "title": "Leads"
                }
            }
        }

        # Create a request to add the "Leads" sheet
        batch_update_request = {
            "requests": [add_sheet_request]
        }

        # Perform batch update to add the "Leads" sheet
        service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=batch_update_request).execute()

        # Once the new sheet is added, update it with the data from the source "Leads" sheet
        paste_data_request = {
            "range": "Leads!A1",  # Paste starting from the first cell of the new sheet
            "values": leads_data
        }

        # Now insert the copied data into the newly created "Leads" sheet
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=paste_data_request["range"],
            valueInputOption="RAW",
            body={"values": paste_data_request["values"]}
        ).execute()

        return "Leads sheet created and data copied successfully!"
    
    except HttpError as err:
        return f"An error occurred: {err}"


# def format_leads_sheet(sheet_id, source_spreadsheet_id, source_sheet_name):
#     service = get_service()

#     # Get the source spreadsheet metadata
#     sheets_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()

#     # Find the sheet ID of the source "leadsxx" sheet
#     source_sheet_id = None
#     for sheet in sheets_metadata['sheets']:
#         if sheet['properties']['title'] == source_sheet_name:
#             source_sheet_id = sheet['properties']['sheetId']
#             break

#     if source_sheet_id is None:
#         return f"Source sheet '{source_sheet_name}' not found in the spreadsheet."

#     # Determine if a "Leads" sheet already exists and get its sheet ID
#     leads_sheet_id = None
#     for sheet in sheets_metadata['sheets']:
#         if sheet['properties']['title'] == 'Leads':
#             leads_sheet_id = sheet['properties']['sheetId']
#             break

#     # If the "Leads" sheet does not exist, create it by copying "leadsxx"
#     if leads_sheet_id is None:
#         # Create a duplicate of the "leadsxx" sheet as "Leads"
#         duplicate_sheet_request = {
#             'duplicateSheet': {
#                 'sourceSheetId': source_sheet_id,
#                 'newSheetName': 'Leads'
#             }
#         }

#         response = service.spreadsheets().batchUpdate(
#             spreadsheetId=sheet_id,
#             body={'requests': [duplicate_sheet_request]}
#         ).execute()

#         # Get the new sheet ID of the "Leads" sheet
#         duplicate_response = response['replies'][0]['duplicateSheet']
#         leads_sheet_id = duplicate_response['properties']['sheetId']

#     return f"'Leads' sheet copied successfully with sheet ID {leads_sheet_id}."


# def copy_leads_sheet_to_target(service, target_spreadsheet_id, source_spreadsheet_id, source_sheet_name):
#     # Get the source spreadsheet metadata
#     source_metadata = service.spreadsheets().get(spreadsheetId=source_spreadsheet_id).execute()

#     # Find the source sheet ID for "leadsxx"
#     source_sheet_id = None
#     for sheet in source_metadata['sheets']:
#         if sheet['properties']['title'] == source_sheet_name:
#             source_sheet_id = sheet['properties']['sheetId']
#             break

#     if source_sheet_id is None:
#         return f"Source sheet '{source_sheet_name}' not found in the source spreadsheet."

#     # Use Google Drive API to copy the entire spreadsheet
#     drive_service = build('drive', 'v3', credentials=service._http.credentials)

#     # Create a copy of the entire source spreadsheet in Drive
#     copied_spreadsheet = drive_service.files().copy(
#         fileId=source_spreadsheet_id, 
#         body={"name": "Temporary Copy"}
#     ).execute()

#     # Get the ID of the new, temporarily copied spreadsheet
#     temp_copied_spreadsheet_id = copied_spreadsheet['id']

#     # Get the lead sheet we are interested in from the copied spreadsheet
#     temp_copied_metadata = service.spreadsheets().get(spreadsheetId=temp_copied_spreadsheet_id).execute()

#     # Find the sheet ID of the source copy within the new temporary spreadsheet
#     temp_leads_sheet_id = None
#     for sheet in temp_copied_metadata['sheets']:
#         if sheet['properties']['title'] == source_sheet_name:
#             temp_leads_sheet_id = sheet['properties']['sheetId']
#             break

#     # Copy the sheet to the target spreadsheet
#     sheet_copy_request = {
#         'destinationSpreadsheetId': target_spreadsheet_id
#     }

#     copied_sheet_response = service.spreadsheets().sheets().copyTo(
#         spreadsheetId=temp_copied_spreadsheet_id,
#         sheetId=temp_leads_sheet_id,
#         body=sheet_copy_request
#     ).execute()

#     # Clean up: delete the temporary spreadsheet copy
#     drive_service.files().delete(fileId=temp_copied_spreadsheet_id).execute()

#     return f"'Leadsxx' sheet copied to target spreadsheet successfully with new sheet ID {copied_sheet_response['sheetId']}."