"""
Item Group Importer

Import Item Groups from CSV/Excel file with custom ID support.

Template columns:
- ID: Custom identifier (used as document name)
- Item Group Name: Display name
- Parent Item Group: ID of parent (empty for root)
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
COLUMNS = ["ID", "Item Group Name", "Parent Item Group", "Is Group"]
EXPECTED_COLUMNS = 4
ROOT_LABEL = "All Item Groups"
PARENT_FIELD = "parent_item_group"
DOCTYPE = "Item Group"


class ItemGroupImporter(Document):
    def validate(self):
        if self.import_file:
            get_item_groups(
                "Item Group Importer",
                ROOT_LABEL,
                file_name=self.import_file,
                for_validate=1
            )


@frappe.whitelist()
def get_item_groups(doctype: str, parent: str, is_root: bool = False,
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
def import_item_groups(file_name: str) -> dict:
    """Main import function."""
    delete_nested_set_items(DOCTYPE)

    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    forest = build_forest(data)
    create_nested_set_items(DOCTYPE, forest)

    frappe.db.commit()

    return {"success": True, "message": _("Item Groups imported successfully")}


@frappe.whitelist()
def get_existing_count() -> dict:
    """Count existing Item Groups."""
    return {"count": count_existing_data(DOCTYPE), "doctype": DOCTYPE}


@frappe.whitelist()
def download_template(file_type: str):
    """Download CSV/Excel template."""
    sample_rows = [
        ["ALL", "All Item Groups", "", "1"],
        ["PROD", "Products", "ALL", "1"],
        ["PROD-FIN", "Finished Products", "PROD", "0"],
        ["PROD-RAW", "Raw Materials", "PROD", "0"],
        ["SERV", "Services", "ALL", "0"],
    ]

    writer = generate_csv_template(COLUMNS, sample_rows)
    download_template_response(writer, file_type, "Item Group Importer")
