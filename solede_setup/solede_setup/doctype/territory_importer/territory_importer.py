"""
Territory Importer

Import Territories from CSV/Excel file.

Template columns:
- ID: Custom identifier
- Territory Name: Display name
- Parent Territory: ID of parent (empty for root)
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
COLUMNS = ["ID", "Territory Name", "Parent Territory", "Is Group"]
EXPECTED_COLUMNS = 4
ROOT_LABEL = "All Territories"
PARENT_FIELD = "parent_territory"
DOCTYPE = "Territory"


class TerritoryImporter(Document):
    def validate(self):
        if self.import_file:
            get_territories(
                "Territory Importer",
                ROOT_LABEL,
                file_name=self.import_file,
                for_validate=1
            )


@frappe.whitelist()
def get_territories(doctype: str, parent: str, is_root: bool = False,
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
def import_territories(file_name: str) -> dict:
    """Main import function."""
    delete_nested_set_items(DOCTYPE)

    data = read_file_data(file_name)
    validate_columns(data, EXPECTED_COLUMNS, COLUMNS)

    forest = build_forest(data)
    create_nested_set_items(DOCTYPE, forest)

    frappe.db.commit()

    return {"success": True, "message": _("Territories imported successfully")}


@frappe.whitelist()
def get_existing_count() -> dict:
    """Count existing Territories."""
    return {"count": count_existing_data(DOCTYPE), "doctype": DOCTYPE}


@frappe.whitelist()
def download_template(file_type: str):
    """Download CSV/Excel template."""
    sample_rows = [
        ["TER-ALL", "All Territories", "", "1"],
        ["TER-EUROPE", "Europe", "TER-ALL", "1"],
        ["TER-ITALY", "Italy", "TER-EUROPE", "0"],
        ["TER-GERMANY", "Germany", "TER-EUROPE", "0"],
        ["TER-ASIA", "Asia", "TER-ALL", "0"],
    ]

    writer = generate_csv_template(COLUMNS, sample_rows)
    download_template_response(writer, file_type, "Territory Importer")
