"""
Solede Setup - Importer Base Module

Funzioni condivise per tutti gli importer:
- Lettura file CSV/Excel
- Validazione colonne
- Costruzione struttura ad albero (forest)
- Preview ad albero

Pattern supportati:
1. NestedSet (Cost Center, Item Group, Territory, etc.)
2. Flat list (Mode of Payment, etc.)
"""

import csv
from functools import reduce

import frappe
from frappe import _
from frappe.utils import cint, cstr
from frappe.utils.csvutils import UnicodeWriter
from frappe.utils.xlsxutils import (
    read_xls_file_from_attached_file,
    read_xlsx_file_from_attached_file,
)


# ============================================================================
# FILE HANDLING
# ============================================================================

def get_file(file_name: str):
    """
    Get file document and validate extension.

    Args:
        file_name: URL del file allegato

    Returns:
        tuple: (file_doc, extension)

    Raises:
        frappe.ValidationError: Se il formato non è supportato
    """
    file_doc = frappe.get_doc("File", {"file_url": file_name})
    parts = file_doc.get_extension()
    extension = parts[1].lstrip(".")

    if extension not in ("csv", "xlsx", "xls"):
        frappe.throw(
            _("Only CSV and Excel files can be used for importing data. "
              "Please check the file format.")
        )

    return file_doc, extension


def generate_data_from_csv(file_doc, as_dict: bool = False) -> list:
    """
    Read CSV file and return data.

    Args:
        file_doc: Frappe File document
        as_dict: Se True, ritorna lista di dizionari

    Returns:
        Lista di righe (liste o dizionari)
    """
    file_path = file_doc.get_full_path()

    data = []
    with open(file_path, encoding="utf-8") as in_file:
        csv_reader = list(csv.reader(in_file))
        headers = csv_reader[0]
        del csv_reader[0]

        for row in csv_reader:
            # Salta righe vuote
            if not any(cell.strip() for cell in row):
                continue

            if as_dict:
                data.append({
                    frappe.scrub(header): row[index] if index < len(row) else ""
                    for index, header in enumerate(headers)
                })
            else:
                data.append(row)

    return data


def generate_data_from_excel(file_doc, extension: str, as_dict: bool = False) -> list:
    """
    Read Excel file and return data.

    Args:
        file_doc: Frappe File document
        extension: "xlsx" o "xls"
        as_dict: Se True, ritorna lista di dizionari

    Returns:
        Lista di righe (liste o dizionari)
    """
    content = file_doc.get_content()

    if extension == "xlsx":
        rows = read_xlsx_file_from_attached_file(fcontent=content)
    elif extension == "xls":
        rows = read_xls_file_from_attached_file(content)
    else:
        frappe.throw(_("Unsupported file extension: {0}").format(extension))

    data = []
    headers = rows[0]
    del rows[0]

    for row in rows:
        # Salta righe vuote
        if not any(cell for cell in row if cell):
            continue

        if as_dict:
            data.append({
                frappe.scrub(header): row[index] if index < len(row) else ""
                for index, header in enumerate(headers)
            })
        else:
            data.append(row)

    return data


def read_file_data(file_name: str, as_dict: bool = False) -> list:
    """
    Read data from CSV or Excel file.

    Args:
        file_name: URL del file allegato
        as_dict: Se True, ritorna lista di dizionari

    Returns:
        Lista di righe
    """
    file_doc, extension = get_file(file_name)

    if extension == "csv":
        return generate_data_from_csv(file_doc, as_dict=as_dict)
    else:
        return generate_data_from_excel(file_doc, extension, as_dict=as_dict)


# ============================================================================
# VALIDATION
# ============================================================================

def validate_columns(data: list, expected_columns: int, column_names: list = None):
    """
    Validate that data has correct number of columns.

    Args:
        data: Lista di righe
        expected_columns: Numero colonne attese
        column_names: Nomi delle colonne (per messaggio errore)

    Raises:
        frappe.ValidationError: Se il numero colonne è errato
    """
    if not data:
        frappe.throw(_("No data found. The file appears to be empty."))

    no_of_columns = max([len(d) for d in data])

    if no_of_columns < expected_columns:
        columns_str = ", ".join(column_names) if column_names else f"{expected_columns} columns"
        frappe.throw(
            _("Expected {0} columns ({1}). Found {2} columns. "
              "Please check the template.").format(
                expected_columns, columns_str, no_of_columns
            ),
            title=_("Wrong Template"),
        )


# ============================================================================
# NESTED SET (TREE) UTILITIES
# ============================================================================

def build_forest(data: list, id_field: int = 0, name_field: int = 1,
                 parent_field: int = 2, is_group_field: int = 3,
                 extra_fields: dict = None) -> dict:
    """
    Convert list of rows into a nested tree structure.

    Struttura input (ogni riga):
    [id, name, parent_id, is_group, ...extra_fields]

    Args:
        data: Lista di righe dal file
        id_field: Indice colonna ID
        name_field: Indice colonna Name
        parent_field: Indice colonna Parent ID
        is_group_field: Indice colonna Is Group
        extra_fields: Dict {field_name: column_index} per campi extra

    Returns:
        Dizionario annidato rappresentante l'albero
    """

    def set_nested(d, path, value):
        """Set value in nested dictionary at given path."""
        reduce(lambda d, k: d.setdefault(k, {}), path[:-1], d)[path[-1]] = value
        return d

    def return_parent(data, child_id):
        """Return the path from root to child."""
        for row in data:
            if len(row) <= max(id_field, parent_field):
                continue

            row_id = cstr(row[id_field]).strip()
            parent_id = cstr(row[parent_field]).strip() if row[parent_field] else ""

            if row_id == child_id:
                if not parent_id or parent_id == row_id:
                    return [row_id]
                else:
                    parent_path = return_parent(data, parent_id)
                    if not parent_path:
                        frappe.throw(
                            _("Parent with ID {0} does not exist in the file").format(
                                frappe.bold(parent_id)
                            )
                        )
                    return [child_id, *parent_path]
        return None

    items_map = {}
    paths = []
    line_no = 2  # Header è riga 1
    error_messages = []

    for row in data:
        min_columns = max(id_field, name_field, parent_field, is_group_field) + 1
        if len(row) < min_columns:
            error_messages.append(
                _("Row {0}: Expected at least {1} columns, found {2}").format(
                    line_no, min_columns, len(row)
                )
            )
            line_no += 1
            continue

        row_id = cstr(row[id_field]).strip()
        item_name = cstr(row[name_field]).strip()
        parent_id = cstr(row[parent_field]).strip() if row[parent_field] else ""
        is_group = cint(row[is_group_field]) if len(row) > is_group_field else 0

        if not row_id:
            error_messages.append(_("Row {0}: ID is required").format(line_no))
            line_no += 1
            continue

        if not item_name:
            error_messages.append(_("Row {0}: Name is required").format(line_no))
            line_no += 1
            continue

        items_map[row_id] = {
            "name": item_name,
            "custom_id": row_id,
        }

        if is_group:
            items_map[row_id]["is_group"] = 1

        # Aggiungi campi extra se specificati
        if extra_fields:
            for field_name, col_index in extra_fields.items():
                if len(row) > col_index and row[col_index]:
                    items_map[row_id][field_name] = cstr(row[col_index]).strip()

        path = return_parent(data, row_id)
        if path:
            paths.append(path[::-1])

        line_no += 1

    if error_messages:
        frappe.throw("<br>".join(error_messages))

    out = {}
    for path in paths:
        for n, item_id in enumerate(path):
            set_nested(out, path[: n + 1], items_map[item_id])

    return out


def build_tree_from_forest(parent: str, chart_data: dict, name_field: str = "name") -> list:
    """
    Build a flat list from forest structure for tree rendering.

    Args:
        parent: Parent ID (empty string for root)
        chart_data: Nested dictionary from build_forest()
        name_field: Nome del campo che contiene il nome visualizzato

    Returns:
        Lista di nodi per frappe.ui.Tree
    """
    result = []

    for key, value in chart_data.items():
        is_group = value.get("is_group", 0)
        display_name = value.get(name_field, key)
        custom_id = value.get("custom_id", key)

        node = {
            "value": custom_id,
            "title": display_name,
            "parent_value": parent,
            "expandable": is_group,
            "is_group": is_group,
            "custom_id": custom_id,
        }

        # Copia tutti gli altri campi
        for field, val in value.items():
            if field not in ("is_group", name_field, "custom_id") and not isinstance(val, dict):
                node[field] = val

        result.append(node)

        # Recursively process children
        children = {k: v for k, v in value.items() if isinstance(v, dict)}
        if children:
            result.extend(build_tree_from_forest(custom_id, children, name_field))

    return result


# ============================================================================
# TEMPLATE GENERATION
# ============================================================================

def generate_csv_template(fields: list, sample_rows: list = None) -> UnicodeWriter:
    """
    Generate a CSV template with headers and optional sample data.

    Args:
        fields: Lista nomi colonne
        sample_rows: Lista di righe di esempio (opzionale)

    Returns:
        UnicodeWriter con il contenuto
    """
    writer = UnicodeWriter()
    writer.writerow(fields)

    if sample_rows:
        for row in sample_rows:
            writer.writerow(row)

    return writer


def download_template_response(writer: UnicodeWriter, file_type: str, doctype_name: str):
    """
    Prepare response for template download.

    Args:
        writer: UnicodeWriter con il contenuto
        file_type: "CSV" o "Excel"
        doctype_name: Nome del DocType per il filename
    """
    import os

    if file_type == "CSV":
        frappe.response["result"] = cstr(writer.getvalue())
        frappe.response["type"] = "csv"
        frappe.response["doctype"] = doctype_name
    else:
        # Excel
        from frappe.utils.xlsxutils import make_xlsx

        filename = frappe.generate_hash("", 10)
        with open(filename, "wb") as f:
            f.write(cstr(writer.getvalue()).encode("utf-8"))

        with open(filename) as f:
            reader = csv.reader(f)
            xlsx_file = make_xlsx(reader, f"{doctype_name} Template")

        os.remove(filename)

        safe_name = doctype_name.lower().replace(" ", "_")
        frappe.response["filename"] = f"{safe_name}_template.xlsx"
        frappe.response["filecontent"] = xlsx_file.getvalue()
        frappe.response["type"] = "binary"


# ============================================================================
# NESTED SET IMPORT UTILITIES
# ============================================================================

def delete_nested_set_items(doctype: str, company: str = None, filters: dict = None):
    """
    Delete all items of a NestedSet DocType for a company.
    Deletes in reverse lft order (children before parents).

    Args:
        doctype: Nome del DocType (es. "Cost Center", "Item Group")
        company: Company filter (opzionale, per DocType legati a company)
        filters: Filtri aggiuntivi (opzionale)
    """
    query_filters = filters or {}
    if company:
        query_filters["company"] = company

    items = frappe.get_all(
        doctype,
        filters=query_filters,
        order_by="lft desc",
        pluck="name"
    )

    for item_name in items:
        try:
            frappe.delete_doc(doctype, item_name, ignore_permissions=True, force=True)
        except Exception as e:
            frappe.logger("solede_setup").warning(
                f"Could not delete {doctype} {item_name}: {e}"
            )

    frappe.db.commit()


def create_nested_set_items(doctype: str, forest: dict, company: str = None,
                            parent: str = None, name_field: str = "name",
                            doctype_name_field: str = None,
                            extra_fields_map: dict = None):
    """
    Recursively create NestedSet items from forest structure.

    Args:
        doctype: Nome del DocType (es. "Cost Center", "Item Group")
        forest: Struttura ad albero da build_forest()
        company: Company (per DocType legati a company)
        parent: Parent name (per ricorsione)
        name_field: Campo nel forest che contiene il nome
        doctype_name_field: Campo nel DocType per il nome (es. "cost_center_name")
        extra_fields_map: Dict {forest_field: doctype_field} per campi extra
    """
    # Determina il campo nome del DocType
    if not doctype_name_field:
        doctype_name_field = frappe.scrub(doctype) + "_name"

    for key, value in forest.items():
        is_group = value.get("is_group", 0)
        item_name = value.get(name_field, key)
        custom_id = value.get("custom_id", key)

        # Crea il documento
        doc = frappe.new_doc(doctype)
        setattr(doc, doctype_name_field, item_name)

        if company:
            doc.company = company

        doc.is_group = is_group

        # Imposta parent usando il campo corretto del DocType
        parent_field = f"parent_{frappe.scrub(doctype)}"
        if hasattr(doc, parent_field):
            setattr(doc, parent_field, parent)

        # Imposta custom_id se il campo esiste
        if hasattr(doc, "custom_id"):
            doc.custom_id = custom_id

        # Imposta campi extra
        if extra_fields_map:
            for forest_field, doctype_field in extra_fields_map.items():
                if forest_field in value and hasattr(doc, doctype_field):
                    setattr(doc, doctype_field, value[forest_field])

        # Flags per evitare validazioni problematiche
        doc.flags.ignore_mandatory = True
        if not parent:
            doc.flags.ignore_validate = True

        doc.insert(ignore_permissions=True)

        # Recursively create children
        children = {k: v for k, v in value.items() if isinstance(v, dict)}
        if children:
            create_nested_set_items(
                doctype=doctype,
                forest=children,
                company=company,
                parent=doc.name,
                name_field=name_field,
                doctype_name_field=doctype_name_field,
                extra_fields_map=extra_fields_map
            )


# ============================================================================
# TREE PREVIEW FOR UI
# ============================================================================

def get_tree_preview_data(
    file_name: str,
    parent: str,
    root_label: str,
    parent_field_name: str,
    expected_columns: int,
    column_names: list,
    for_validate: int = 0
) -> list | dict:
    """
    Generic function to get tree preview data for NestedSet importers.

    Args:
        file_name: URL del file allegato
        parent: Parent node from tree UI
        root_label: Label del nodo root (es. "All Item Groups")
        parent_field_name: Nome del campo parent nel risultato (es. "parent_item_group")
        expected_columns: Numero colonne attese
        column_names: Nomi delle colonne
        for_validate: Se 1, solo validazione senza ritornare dati

    Returns:
        Lista di nodi per frappe.ui.Tree o dict di validazione
    """
    get_file(file_name)  # Validates file exists and format
    parent = None if parent == _(root_label) else parent

    data = read_file_data(file_name)
    validate_columns(data, expected_columns, column_names)

    if not cint(for_validate):
        forest = build_forest(data)
        items = build_tree_from_forest("", chart_data=forest, name_field="name")

        # Rename parent_value to the specific parent field name
        for item in items:
            item[parent_field_name] = item.pop("parent_value", "")

        # Filter to show data for the selected node only
        if parent is None:
            items = [d for d in items if not d.get(parent_field_name)]
        else:
            items = [d for d in items if d.get(parent_field_name) == parent]

        return items
    else:
        return {"show_import_button": 1}


# ============================================================================
# EXISTING DATA CHECK
# ============================================================================

def count_existing_data(doctype: str, company: str = None, filters: dict = None) -> int:
    """
    Count existing records for a DocType.

    Args:
        doctype: Nome del DocType
        company: Company filter (opzionale)
        filters: Filtri aggiuntivi (opzionale)

    Returns:
        Numero di record esistenti
    """
    query_filters = filters or {}
    if company:
        query_filters["company"] = company

    return frappe.db.count(doctype, query_filters)
