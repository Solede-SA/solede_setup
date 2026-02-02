"""
Warehouse Importer

Import Warehouses from CSV/Excel file.

Template columns:
- ID: Custom identifier
- Warehouse Name: Display name
- Parent Warehouse: ID of parent (empty for root)
- Is Group: 1 for group, 0 for leaf
"""

import frappe
from frappe import _
from frappe.model.document import Document

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
COLUMNS = ["ID", "Warehouse Name", "Parent Warehouse", "Is Group"]
EXPECTED_COLUMNS = 4
ROOT_LABEL = "All Warehouses"
PARENT_FIELD = "parent_warehouse"
DOCTYPE = "Warehouse"


class WarehouseImporter(Document):
    def validate(self):
        if self.import_file:
            get_warehouses(
                "Warehouse Importer",
                ROOT_LABEL,
                file_name=self.import_file,
                for_validate=1
            )


@frappe.whitelist()
def get_warehouses(doctype: str, parent: str, is_root: bool = False,
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
def import_warehouses(file_name: str, company: str) -> dict:
    """Main import function."""
    delete_nested_set_items(DOCTYPE, company=company)

    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    forest = build_forest(data)
    create_nested_set_items(DOCTYPE, forest, company=company)

    frappe.db.commit()

    return {"success": True, "message": _("Warehouses imported successfully")}


@frappe.whitelist()
def get_existing_count(company: str) -> dict:
    """Count existing Warehouses for the company."""
    return {"count": count_existing_data(DOCTYPE, company=company), "doctype": DOCTYPE}


@frappe.whitelist()
def download_template(file_type: str):
    """Download CSV/Excel template."""
    sample_rows = [
        ["WH-ALL", "All Warehouses", "", "1"],
        ["WH-MAIN", "Main Warehouse", "WH-ALL", "1"],
        ["WH-STORE", "Stores", "WH-MAIN", "0"],
        ["WH-FG", "Finished Goods", "WH-MAIN", "0"],
        ["WH-WIP", "Work In Progress", "WH-ALL", "0"],
    ]

    writer = generate_csv_template(COLUMNS, sample_rows)
    download_template_response(writer, file_type, "Warehouse Importer")
