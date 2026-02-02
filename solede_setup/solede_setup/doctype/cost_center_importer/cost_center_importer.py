"""
Cost Center Importer

Import Cost Centers from CSV/Excel file with custom ID support.

Template columns:
- ID: Custom identifier (used as document name)
- Cost Center Name: Display name
- Parent Cost Center: ID of parent (empty for root)
- Is Group: 1 for group, 0 for leaf
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from solede_setup.utils.importer_base import (
    read_file_data,
    validate_columns,
    build_forest,
    generate_csv_template,
    download_template_response,
    delete_nested_set_items,
    create_nested_set_items,
    get_tree_preview_data,
    count_existing_data,
)

# Column configuration
COLUMNS = ["ID", "Cost Center Name", "Parent Cost Center", "Is Group"]
EXPECTED_COLUMNS = 4
ROOT_LABEL = "All Cost Centers"
PARENT_FIELD = "parent_cost_center"
DOCTYPE = "Cost Center"


class CostCenterImporter(Document):
    def validate(self):
        if self.import_file:
            get_cost_centers(
                "Cost Center Importer",
                ROOT_LABEL,
                file_name=self.import_file,
                for_validate=1
            )


@frappe.whitelist()
def validate_company(company: str) -> dict:
    """Check if company has GL entries with cost centers."""
    gl_entries_count = frappe.db.count(
        "GL Entry",
        {"company": company, "cost_center": ["is", "set"]}
    )

    if gl_entries_count > 0:
        return {"has_gl_entries": True, "count": gl_entries_count}
    return {"has_gl_entries": False, "count": 0}


@frappe.whitelist()
def get_cost_centers(doctype: str, parent: str, is_root: bool = False,
                     file_name: str = None, for_validate: int = 0) -> list | dict:
    """Called by tree view to fetch node's children."""
    return get_tree_preview_data(
        file_name=file_name,
        parent=parent,
        root_label=ROOT_LABEL,
        parent_field_name=PARENT_FIELD,
        expected_columns=EXPECTED_COLUMNS,
        column_names=COLUMNS,
        for_validate=for_validate
    )


@frappe.whitelist()
def import_cost_centers(file_name: str, company: str, force_delete_gl_entries: int = 0) -> dict:
    """Main import function."""
    force_delete_gl_entries = cint(force_delete_gl_entries)

    # Check for GL entries with cost centers
    validation = validate_company(company)
    if validation.get("has_gl_entries"):
        if force_delete_gl_entries:
            deleted_count = _delete_gl_entries_with_cost_center(company)
            frappe.msgprint(
                _("Deleted {0} GL Entries with Cost Centers").format(deleted_count),
                indicator="orange",
                alert=True
            )
        else:
            frappe.throw(
                _("Cannot import Cost Centers. {0} GL Entries with Cost Centers exist for this company. "
                  "Enable 'Force Delete GL Entries' to delete them.").format(
                    validation.get("count")
                )
            )

    # Reset company cost center fields
    frappe.db.set_value(
        "Company",
        company,
        {
            "cost_center": "",
            "round_off_cost_center": "",
            "depreciation_cost_center": "",
        },
    )

    # Delete existing cost centers
    delete_nested_set_items(DOCTYPE, company=company)

    # Read and validate file
    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    # Build forest and create cost centers
    forest = build_forest(data)
    create_nested_set_items(DOCTYPE, forest, company=company)

    # Set default cost center
    _set_default_cost_center(company)

    frappe.db.commit()

    return {"success": True, "message": _("Cost Centers imported successfully")}


def _delete_gl_entries_with_cost_center(company: str) -> int:
    """Delete all GL Entries with Cost Centers for the company."""
    gl_entries = frappe.get_all(
        "GL Entry",
        filters={"company": company, "cost_center": ["is", "set"]},
        pluck="name"
    )

    for gl_entry in gl_entries:
        frappe.delete_doc("GL Entry", gl_entry, ignore_permissions=True, force=True)

    frappe.db.commit()
    return len(gl_entries)


def _set_default_cost_center(company: str):
    """Set the root cost center as default for the company."""
    root_cost_center = frappe.db.get_value(
        DOCTYPE,
        {"company": company, "parent_cost_center": ["is", "not set"]},
        "name"
    )

    if root_cost_center:
        frappe.db.set_value("Company", company, "cost_center", root_cost_center)


@frappe.whitelist()
def get_existing_count(company: str) -> dict:
    """Count existing Cost Centers for the company."""
    return {"count": count_existing_data(DOCTYPE, company=company), "doctype": DOCTYPE}


@frappe.whitelist()
def download_template(file_type: str):
    """Download CSV/Excel template."""
    sample_rows = [
        ["ROOT001", "Main Cost Center", "", "1"],
        ["SALES001", "Sales", "ROOT001", "1"],
        ["SALES-IT", "Sales Italy", "SALES001", "0"],
        ["SALES-EU", "Sales Europe", "SALES001", "0"],
        ["ADMIN001", "Administration", "ROOT001", "0"],
    ]

    writer = generate_csv_template(COLUMNS, sample_rows)
    download_template_response(writer, file_type, "Cost Center Importer")
