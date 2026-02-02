"""
Mode of Payment Importer

Import Modes of Payment from CSV/Excel file.

Template columns:
- Mode of Payment: Name (unique identifier)
- Type: Cash, Bank, General, Phone
- Enabled: 1 for enabled, 0 for disabled
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from solede_setup.utils.importer_base import (
    get_file,
    read_file_data,
    validate_columns,
    generate_csv_template,
    download_template_response,
    count_existing_data,
)

# Column configuration
COLUMNS = ["Mode of Payment", "Type", "Enabled"]
EXPECTED_COLUMNS = 3


class ModeofPaymentImporter(Document):
    def validate(self):
        if self.import_file:
            get_preview_data(file_name=self.import_file, for_validate=1)


@frappe.whitelist()
def get_preview_data(file_name: str = None, for_validate: int = 0) -> list | dict:
    """Get preview data for display."""
    file_doc, extension = get_file(file_name)

    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    if not cint(for_validate):
        preview_data = []
        for row in data:
            preview_data.append({
                "mode_of_payment": row[0].strip() if len(row) > 0 else "",
                "type": row[1].strip() if len(row) > 1 else "General",
                "enabled": cint(row[2]) if len(row) > 2 else 1,
            })
        return preview_data
    else:
        return {"show_import_button": 1}


@frappe.whitelist()
def import_modes_of_payment(file_name: str) -> dict:
    """Main import function."""
    # Delete existing modes of payment
    existing = frappe.get_all("Mode of Payment", pluck="name")
    for name in existing:
        frappe.delete_doc("Mode of Payment", name, ignore_permissions=True, force=True)

    # Read and validate file
    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    # Create modes of payment
    for row in data:
        mode_name = row[0].strip() if len(row) > 0 else ""
        if not mode_name:
            continue

        mode_type = row[1].strip() if len(row) > 1 else "General"
        enabled = cint(row[2]) if len(row) > 2 else 1

        # Validate type
        if mode_type not in ("Cash", "Bank", "General", "Phone"):
            mode_type = "General"

        doc = frappe.new_doc("Mode of Payment")
        doc.mode_of_payment = mode_name
        doc.type = mode_type
        doc.enabled = enabled
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)

    frappe.db.commit()

    return {"success": True, "message": _("Modes of Payment imported successfully")}


@frappe.whitelist()
def get_existing_count() -> dict:
    """Count existing Modes of Payment."""
    return {"count": count_existing_data("Mode of Payment"), "doctype": "Mode of Payment"}


@frappe.whitelist()
def download_template(file_type: str):
    """Download CSV/Excel template."""
    sample_rows = [
        ["Cash", "Cash", "1"],
        ["Bank Transfer", "Bank", "1"],
        ["Credit Card", "Bank", "1"],
        ["Check", "Bank", "1"],
        ["Wire Transfer", "Bank", "1"],
    ]

    writer = generate_csv_template(COLUMNS, sample_rows)
    download_template_response(writer, file_type, "Mode of Payment Importer")
