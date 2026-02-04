"""
Payment Terms Importer

Import Payment Terms from CSV/Excel file.

Template columns:
- Payment Term Name: Name (unique identifier)
- Description: Description of the term
- Due Date Based On: Day(s) after invoice date, Day(s) after the end of the invoice month, Month(s) after the end of the invoice month
- Credit Days: Number of days
- Credit Months: Number of months
- Invoice Portion: Percentage (0-100), default 100
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from solede_setup.utils.importer_base import (
    get_file,
    read_file_data,
    validate_columns,
    generate_csv_template,
    download_template_response,
    count_existing_data,
)

# Column configuration
COLUMNS = ["Payment Term Name", "Description", "Due Date Based On", "Credit Days", "Credit Months", "Invoice Portion"]
EXPECTED_COLUMNS = 6

# Valid options for Due Date Based On
DUE_DATE_OPTIONS = [
    "Day(s) after invoice date",
    "Day(s) after the end of the invoice month",
    "Month(s) after the end of the invoice month"
]


class PaymentTermsImporter(Document):
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
                "payment_term_name": row[0].strip() if len(row) > 0 else "",
                "description": row[1].strip() if len(row) > 1 else "",
                "due_date_based_on": row[2].strip() if len(row) > 2 else DUE_DATE_OPTIONS[0],
                "credit_days": cint(row[3]) if len(row) > 3 else 0,
                "credit_months": cint(row[4]) if len(row) > 4 else 0,
                "invoice_portion": flt(row[5]) if len(row) > 5 else 100,
            })
        return preview_data
    else:
        return {"show_import_button": 1}


@frappe.whitelist()
def import_payment_terms(file_name: str) -> dict:
    """Main import function."""
    # Delete existing payment terms
    existing = frappe.get_all("Payment Term", pluck="name")
    for name in existing:
        frappe.delete_doc("Payment Term", name, ignore_permissions=True, force=True)

    # Read and validate file
    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    # Create payment terms
    for row in data:
        term_name = row[0].strip() if len(row) > 0 else ""
        if not term_name:
            continue

        description = row[1].strip() if len(row) > 1 else ""
        due_date_based_on = row[2].strip() if len(row) > 2 else DUE_DATE_OPTIONS[0]
        credit_days = cint(row[3]) if len(row) > 3 else 0
        credit_months = cint(row[4]) if len(row) > 4 else 0
        invoice_portion = flt(row[5]) if len(row) > 5 else 100

        # Validate due_date_based_on
        if due_date_based_on not in DUE_DATE_OPTIONS:
            due_date_based_on = DUE_DATE_OPTIONS[0]

        doc = frappe.new_doc("Payment Term")
        doc.payment_term_name = term_name
        doc.description = description
        doc.due_date_based_on = due_date_based_on
        doc.credit_days = credit_days
        doc.credit_months = credit_months
        doc.invoice_portion = invoice_portion
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)

    frappe.db.commit()

    return {"success": True, "message": _("Payment Terms imported successfully")}


@frappe.whitelist()
def get_existing_count() -> dict:
    """Count existing Payment Terms."""
    return {"count": count_existing_data("Payment Term"), "doctype": "Payment Term"}


@frappe.whitelist()
def download_template(file_type: str):
    """Download CSV/Excel template."""
    sample_rows = [
        ["Net 30", "Payment due in 30 days", "Day(s) after invoice date", "30", "0", "100"],
        ["Net 60", "Payment due in 60 days", "Day(s) after invoice date", "60", "0", "100"],
        ["Due on Receipt", "Payment due immediately", "Day(s) after invoice date", "0", "0", "100"],
        ["End of Month", "Payment due at end of month", "Day(s) after the end of the invoice month", "0", "0", "100"],
        ["Net 30 EOM", "30 days after end of invoice month", "Month(s) after the end of the invoice month", "0", "1", "100"],
    ]

    writer = generate_csv_template(COLUMNS, sample_rows)
    download_template_response(writer, file_type, "Payment Terms Importer")
