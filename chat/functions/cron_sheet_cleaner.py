import re

from chat.service import get_service

def process_sales(sheet_id):
    service = get_service()  # Assumes get_service() initializes the Google Sheets API client.

    # Fetch data from the Sales sheet
    sales_range = "Sales!A:E"
    sales_result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=sales_range
    ).execute()

    sales_values = sales_result.get('values', [])
    if not sales_values or len(sales_values) < 2:
        print("No sufficient data found in the 'Sales' sheet.")
        return False

    # Header for reference
    sales_header = sales_values[0]

    # Hold indices for columns we're interacting with
    status_idx = sales_header.index("Status")
    date_time_idx = sales_header.index("Date Time")
    product_name_idx = sales_header.index("Product Name")
    quantity_idx = sales_header.index("Quantity")
    live_cost_idx = sales_header.index("Live Cost")

    # First Condition Check and Update
    updated_status_rows = []

    for i, row in enumerate(sales_values[1:], start=2):  # Start from 2 to account for header
        # Skip processing if "Date Time" is missing or empty
        if len(row) <= date_time_idx or not row[date_time_idx]:
            continue

        # Ensure the row has enough elements for the status index
        if len(row) <= status_idx:
            row.extend([''] * (status_idx - len(row) + 1))

        if row[status_idx] in ("", "Confirm"):
            row[status_idx] = "Updating"
            updated_status_rows.append(i)

    if updated_status_rows:
        # If we updated any statuses, write back to Google Sheets and exit
        update_range = f"Sales!E2:E{len(sales_values)}"
        update_body = {
            "range": update_range,
            "values": [[row[status_idx] if len(row) > status_idx else ""] for row in sales_values[1:]]
        }
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=update_range,
            valueInputOption="USER_ENTERED",
            body=update_body
        ).execute()
        print(f"Updated Status to 'Updating' for rows: {updated_status_rows}")
        return True

    # Second Condition - Handle 'Updating' statuses
    if not any((len(row) <= status_idx or row[status_idx] in ("", "Confirm")) and len(row) > date_time_idx and row[date_time_idx] for row in sales_values[1:]):
        # Fetch data from the Inventory sheet
        inventory_range = "Inventory!A:E"
        inventory_result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=inventory_range
        ).execute()

        inventory_values = inventory_result.get('values', [])
        if not inventory_values or len(inventory_values) < 2:
            print("No sufficient data found in the 'Inventory' sheet.")
            return False

        inventory_header = inventory_values[0]
        inventory_name_idx = inventory_header.index("Name")
        inventory_stocks_idx = inventory_header.index("Stocks")

        # Track total costs per Date Time
        date_time_costs = {}

        for row in sales_values[1:]:
            if len(row) > date_time_idx and row[date_time_idx] and row[status_idx] == "Updating":
                # Deduct quantity from inventory
                sales_product_name = row[product_name_idx]
                sales_quantity = int(row[quantity_idx])

                inventory_row = next((inv_row for inv_row in inventory_values[1:] if len(inv_row) > inventory_name_idx and inv_row[inventory_name_idx] == sales_product_name), None)

                if inventory_row:
                    current_stocks = int(inventory_row[inventory_stocks_idx])
                    inventory_row[inventory_stocks_idx] = str(current_stocks - sales_quantity)

                    # Track the costs, removing any non-numeric characters (e.g., currency symbols)
                    sales_date_time = row[date_time_idx]
                    sales_live_cost_str = row[live_cost_idx]
                    sales_live_cost_float = float(re.sub(r"[^\d.]", "", sales_live_cost_str))
                    date_time_costs[sales_date_time] = date_time_costs.get(sales_date_time, 0) + sales_live_cost_float

                else:
                    # Mark as 'Not Exist' if no inventory match
                    row[status_idx] = "Not Exist"

        # Update Inventory sheet stocks
        inventory_update_range = f"Inventory!A2:E{len(inventory_values)}"
        inventory_update_body = {
            "range": inventory_update_range,
            "values": inventory_values[1:]
        }
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=inventory_update_range,
            valueInputOption="USER_ENTERED",
            body=inventory_update_body
        ).execute()

        # Update Sales sheet for any 'Not Exist' statuses and set "Updating" to "Done"
        for row in sales_values[1:]:
            if len(row) > status_idx and row[status_idx] == "Updating":
                row[status_idx] = "Done"

        sales_update_range = f"Sales!E2:E{len(sales_values)}"
        sales_update_body = {
            "range": sales_update_range,
            "values": [[row[status_idx] if len(row) > status_idx else ""] for row in sales_values[1:]]
        }
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=sales_update_range,
            valueInputOption="USER_ENTERED",
            body=sales_update_body
        ).execute()

        # Insert records into Transactions sheet
        transactions_range = "Transactions!A:B"
        transaction_values = [[date_time, total_cost] for date_time, total_cost in date_time_costs.items()]
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=transactions_range,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": transaction_values}
        ).execute()

        print("Processed 'Updating' rows in Sales, adjusted Inventory, and recorded Transactions. All 'Updating' statuses set to 'Done'.")
        return True

    return False