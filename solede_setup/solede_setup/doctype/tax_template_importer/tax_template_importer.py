"""
Tax Template Importer

Import Sales, Purchase, and Item Tax Templates from CSV/Excel file.

Template columns:
- Template Type: "Sales", "Purchase", or "Item"
- Template Title: Name of the template
- Is Default: 1 for default, 0 otherwise (only for Sales/Purchase)
- Charge Type: Actual, On Net Total, etc. (only for Sales/Purchase, leave empty for Item)
- Account Head: Account name for the tax
- Rate: Tax rate percentage
- Description: Description of the charge (only for Sales/Purchase)

Multiple rows with the same Template Type + Template Title are grouped into one template
with multiple tax lines.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, cstr

from solede_setup.utils.importer_base import (
    get_file,
    read_file_data,
    validate_columns,
    generate_csv_template,
    download_template_response,
)

# Column configuration
COLUMNS = [
    "Template Type",
    "Template Title",
    "Is Default",
    "Charge Type",
    "Account Head",
    "Rate",
    "Description"
]
EXPECTED_COLUMNS = 7

# Valid charge types for Sales/Purchase
CHARGE_TYPES = [
    "Actual",
    "On Net Total",
    "On Previous Row Amount",
    "On Previous Row Total",
    "On Item Quantity"
]


class TaxTemplateImporter(Document):
    def validate(self):
        if self.import_file and self.company:
            get_preview_data(
                file_name=self.import_file,
                company=self.company,
                for_validate=1
            )


@frappe.whitelist()
def get_preview_data(file_name: str, company: str, for_validate: int = 0) -> list | dict:
    """Get preview data for display."""
    file_doc, extension = get_file(file_name)

    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    if not cint(for_validate):
        templates = _group_rows_by_template(data)
        return templates
    else:
        return {"show_import_button": 1}


def _normalize_template_type(template_type: str) -> str:
    """Normalize template type to standard values."""
    t = template_type.lower().strip()
    if t in ("sales", "vendita", "vendite"):
        return "Sales"
    elif t in ("purchase", "acquisto", "acquisti"):
        return "Purchase"
    elif t in ("item", "articolo", "articoli"):
        return "Item"
    return template_type


def _group_rows_by_template(data: list) -> list:
    """Group CSV rows by template type and title."""
    templates_dict = {}

    for row in data:
        template_type = cstr(row[0]).strip() if len(row) > 0 else ""
        template_title = cstr(row[1]).strip() if len(row) > 1 else ""
        is_default = cint(row[2]) if len(row) > 2 else 0
        charge_type = cstr(row[3]).strip() if len(row) > 3 else ""
        account_head = cstr(row[4]).strip() if len(row) > 4 else ""
        rate = flt(row[5]) if len(row) > 5 else 0
        description = cstr(row[6]).strip() if len(row) > 6 else ""

        if not template_type or not template_title:
            continue

        template_type = _normalize_template_type(template_type)
        key = f"{template_type}::{template_title}"

        if key not in templates_dict:
            templates_dict[key] = {
                "template_type": template_type,
                "template_title": template_title,
                "is_default": is_default,
                "taxes": []
            }

        if account_head:
            tax_entry = {
                "account_head": account_head,
                "rate": rate,
            }
            # Only add charge_type and description for Sales/Purchase
            if template_type in ("Sales", "Purchase"):
                tax_entry["charge_type"] = charge_type or "On Net Total"
                tax_entry["description"] = description or f"{charge_type or 'Tax'} @ {rate}%"

            templates_dict[key]["taxes"].append(tax_entry)

    return list(templates_dict.values())


@frappe.whitelist()
def import_tax_templates(file_name: str, company: str) -> dict:
    """Main import function."""
    # Delete existing tax templates for this company
    _delete_existing_templates(company)

    # Read and validate file
    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    # Group rows by template and create
    templates = _group_rows_by_template(data)
    _create_templates(templates, company)

    frappe.db.commit()

    return {"success": True, "message": _("Tax Templates imported successfully")}


def _delete_existing_templates(company: str):
    """Delete existing Sales, Purchase, and Item Tax Templates for the company."""
    # Delete Sales Tax Templates
    for name in frappe.get_all(
        "Sales Taxes and Charges Template",
        filters={"company": company},
        pluck="name"
    ):
        frappe.delete_doc(
            "Sales Taxes and Charges Template", name,
            ignore_permissions=True, force=True
        )

    # Delete Purchase Tax Templates
    for name in frappe.get_all(
        "Purchase Taxes and Charges Template",
        filters={"company": company},
        pluck="name"
    ):
        frappe.delete_doc(
            "Purchase Taxes and Charges Template", name,
            ignore_permissions=True, force=True
        )

    # Delete Item Tax Templates
    for name in frappe.get_all(
        "Item Tax Template",
        filters={"company": company},
        pluck="name"
    ):
        frappe.delete_doc(
            "Item Tax Template", name,
            ignore_permissions=True, force=True
        )


def _create_templates(templates: list, company: str):
    """Create tax templates from grouped data."""
    for template_data in templates:
        template_type = template_data["template_type"]
        template_title = template_data["template_title"]
        is_default = template_data["is_default"]
        taxes = template_data["taxes"]

        if template_type == "Sales":
            _create_sales_template(template_title, company, is_default, taxes)
        elif template_type == "Purchase":
            _create_purchase_template(template_title, company, is_default, taxes)
        elif template_type == "Item":
            _create_item_template(template_title, company, taxes)


def _create_sales_template(title: str, company: str, is_default: int, taxes: list):
    """Create a Sales Taxes and Charges Template."""
    doc = frappe.new_doc("Sales Taxes and Charges Template")
    doc.title = title
    doc.company = company
    doc.is_default = is_default

    for tax in taxes:
        charge_type = tax.get("charge_type", "On Net Total")
        if charge_type not in CHARGE_TYPES:
            frappe.throw(
                _("Invalid charge type '{0}' in template '{1}'. Valid: {2}").format(
                    charge_type, title, ", ".join(CHARGE_TYPES)
                )
            )

        account_name = _find_account(tax["account_head"], company)
        doc.append("taxes", {
            "charge_type": charge_type,
            "account_head": account_name,
            "rate": tax["rate"],
            "description": tax.get("description", "")
        })

    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)


def _create_purchase_template(title: str, company: str, is_default: int, taxes: list):
    """Create a Purchase Taxes and Charges Template."""
    doc = frappe.new_doc("Purchase Taxes and Charges Template")
    doc.title = title
    doc.company = company
    doc.is_default = is_default

    for tax in taxes:
        charge_type = tax.get("charge_type", "On Net Total")
        if charge_type not in CHARGE_TYPES:
            frappe.throw(
                _("Invalid charge type '{0}' in template '{1}'. Valid: {2}").format(
                    charge_type, title, ", ".join(CHARGE_TYPES)
                )
            )

        account_name = _find_account(tax["account_head"], company)
        doc.append("taxes", {
            "category": "Total",
            "add_deduct_tax": "Add",
            "charge_type": charge_type,
            "account_head": account_name,
            "rate": tax["rate"],
            "description": tax.get("description", "")
        })

    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)


def _create_item_template(title: str, company: str, taxes: list):
    """Create an Item Tax Template."""
    doc = frappe.new_doc("Item Tax Template")
    doc.title = title
    doc.company = company

    for tax in taxes:
        account_name = _find_account(tax["account_head"], company)
        doc.append("taxes", {
            "tax_type": account_name,
            "tax_rate": tax["rate"]
        })

    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)


def _find_account(account_identifier: str, company: str) -> str:
    """Find account by name or account number."""
    # Try exact match
    if frappe.db.exists("Account", account_identifier):
        return account_identifier

    # Try with company abbreviation
    abbr = frappe.get_cached_value("Company", company, "abbr")
    account_with_company = f"{account_identifier} - {abbr}"
    if frappe.db.exists("Account", account_with_company):
        return account_with_company

    # Try by account_name field
    account = frappe.db.get_value(
        "Account",
        {"account_name": account_identifier, "company": company},
        "name"
    )
    if account:
        return account

    # Try by account_number
    account = frappe.db.get_value(
        "Account",
        {"account_number": account_identifier, "company": company},
        "name"
    )
    if account:
        return account

    frappe.throw(
        _("Account '{0}' not found for company '{1}'").format(
            account_identifier, company
        )
    )


@frappe.whitelist()
def get_existing_count(company: str) -> dict:
    """Count existing Tax Templates for the company."""
    sales_count = frappe.db.count("Sales Taxes and Charges Template", {"company": company})
    purchase_count = frappe.db.count("Purchase Taxes and Charges Template", {"company": company})
    item_count = frappe.db.count("Item Tax Template", {"company": company})
    total = sales_count + purchase_count + item_count
    return {
        "count": total,
        "sales": sales_count,
        "purchase": purchase_count,
        "item": item_count,
        "doctype": "Tax Templates"
    }


@frappe.whitelist()
def download_template(file_type: str):
    """Download CSV/Excel template."""
    sample_rows = [
        ["Sales", "IVA 22%", "1", "On Net Total", "IVA su vendite 22%", "22", "IVA 22%"],
        ["Sales", "IVA 10%", "0", "On Net Total", "IVA su vendite 10%", "10", "IVA 10% ridotta"],
        ["Purchase", "IVA 22%", "1", "On Net Total", "IVA su acquisti 22%", "22", "IVA 22%"],
        ["Purchase", "IVA 10%", "0", "On Net Total", "IVA su acquisti 10%", "10", "IVA 10% ridotta"],
        ["Item", "IVA 22%", "", "", "IVA su vendite 22%", "22", ""],
        ["Item", "IVA 10%", "", "", "IVA su vendite 10%", "10", ""],
        ["Item", "IVA 4%", "", "", "IVA su vendite 4%", "4", ""],
    ]

    writer = generate_csv_template(COLUMNS, sample_rows)
    download_template_response(writer, file_type, "Tax Template Importer")
