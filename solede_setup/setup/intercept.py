"""
Solede Setup - Intercept Hooks

Questo modulo intercetta gli automatismi di setup di ERPNext per:
1. Loggare tutto ciò che viene creato automaticamente
2. Permettere all'utente di controllare cosa viene creato
3. Dare la possibilità di pulire/modificare i dati creati

PUNTI DI INTERCETTAZIONE:
- setup_wizard_complete: dopo che il wizard ERPNext ha finito
- doc_events: intercetta creazione di Account, Item Group, Territory, ecc.
- Company.after_insert: intercetta quando Company triggera creazioni automatiche
"""

import frappe
from frappe import _


# ============================================================================
# CONFIGURAZIONE INTERCETTAZIONE
# ============================================================================

# DocTypes da tracciare durante il setup
TRACKED_DOCTYPES = [
    "Account",
    "Warehouse",
    "Cost Center",
    "Department",
    "Item Group",
    "Territory",
    "Customer Group",
    "Supplier Group",
    "Sales Taxes and Charges Template",
    "Purchase Taxes and Charges Template",
    "Item Tax Template",
    "Mode of Payment",
    "Price List",
    "Stock Entry Type",
    "UOM",
    "Payment Term",
    "Payment Terms Template",
]

# Flag per abilitare/disabilitare il tracking
# Viene impostato True durante il setup wizard
_tracking_enabled = False


# ============================================================================
# SETUP LOG - Tracciamento creazioni
# ============================================================================

def log_creation(doctype: str, docname: str, source: str = "erpnext_auto"):
    """
    Logga la creazione di un documento durante il setup.

    Args:
        doctype: Tipo documento creato
        docname: Nome documento creato
        source: Sorgente creazione (erpnext_auto, solede_setup, user)
    """
    if not is_tracking_enabled():
        return

    try:
        # Usa frappe.db.sql diretto per evitare ricorsione
        frappe.db.sql("""
            INSERT INTO `tabSetup Log`
            (name, creation, modified, owner, docstatus, doctype_name, document_name, source, created_at)
            VALUES (%(name)s, NOW(), NOW(), %(owner)s, 0, %(doctype_name)s, %(document_name)s, %(source)s, NOW())
        """, {
            "name": frappe.generate_hash(length=10),
            "owner": frappe.session.user or "Administrator",
            "doctype_name": doctype,
            "document_name": docname,
            "source": source
        })
        frappe.db.commit()
    except Exception:
        # Se Setup Log non esiste ancora, ignora silenziosamente
        pass


def is_tracking_enabled() -> bool:
    """Verifica se il tracking è abilitato."""
    global _tracking_enabled
    return _tracking_enabled or frappe.flags.get("solede_setup_tracking", False)


def enable_tracking():
    """Abilita il tracking delle creazioni."""
    global _tracking_enabled
    _tracking_enabled = True
    frappe.flags.solede_setup_tracking = True


def disable_tracking():
    """Disabilita il tracking delle creazioni."""
    global _tracking_enabled
    _tracking_enabled = False
    frappe.flags.solede_setup_tracking = False


# ============================================================================
# SETUP WIZARD HOOKS
# ============================================================================

def post_wizard_cleanup(args):
    """
    Hook: setup_wizard_complete

    Eseguito DOPO che il wizard ERPNext ha completato tutti gli stage.
    Qui possiamo:
    - Analizzare cosa è stato creato
    - Applicare pulizia secondo Setup Profile
    - Applicare template custom
    - Loggare il completamento

    Args:
        args: Dizionario con i parametri del wizard (company_name, country, ecc.)
    """
    company_name = args.get("company_name")

    frappe.logger("solede_setup").info(
        f"Setup wizard completed for company: {company_name}"
    )

    # Disabilita tracking dopo il wizard
    disable_tracking()

    # Applica Setup Profile se attivo
    _apply_setup_profile(args)

    # Notifica completamento
    frappe.publish_realtime(
        "solede_setup_complete",
        {"company": company_name},
        user=frappe.session.user
    )


def _apply_setup_profile(args):
    """
    Applica le configurazioni del Setup Profile attivo.

    Questo include:
    - Eliminare documenti che dovevano essere skippati
    - Applicare template custom (se specificati)
    """
    try:
        from solede_setup.solede_setup.doctype.setup_profile.setup_profile import get_active_profile
    except ImportError:
        frappe.logger("solede_setup").warning("Setup Profile not available yet")
        return

    profile = get_active_profile()
    if not profile:
        frappe.logger("solede_setup").info("No active Setup Profile - keeping all defaults")
        return

    frappe.logger("solede_setup").info(f"Applying Setup Profile: {profile.name}")

    company = args.get("company_name")

    # Mapping: campo skip -> (DocType, documenti default da eliminare)
    skip_mapping = {
        "skip_default_item_groups": ("Item Group", _get_default_item_groups),
        "skip_default_territories": ("Territory", _get_default_territories),
        "skip_default_customer_groups": ("Customer Group", _get_default_customer_groups),
        "skip_default_supplier_groups": ("Supplier Group", _get_default_supplier_groups),
        "skip_default_mode_of_payment": ("Mode of Payment", _get_default_mode_of_payment),
        "skip_default_stock_entry_types": ("Stock Entry Type", _get_default_stock_entry_types),
        "skip_default_price_lists": ("Price List", _get_default_price_lists),
    }

    for skip_field, (doctype, get_defaults_fn) in skip_mapping.items():
        if getattr(profile, skip_field, False):
            _delete_default_documents(doctype, get_defaults_fn())

    # Elimina tax templates se richiesto
    if profile.skip_default_tax_templates:
        _delete_company_tax_templates(company)

    # Elimina warehouse default se richiesto
    if getattr(profile, "skip_default_warehouses", False):
        _delete_company_warehouses(company)

    # Applica template custom se specificati
    _apply_custom_templates(profile, company)


def _delete_default_documents(doctype: str, default_names: list):
    """Elimina documenti default per un DocType."""
    for name in default_names:
        try:
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
                frappe.logger("solede_setup").info(f"Deleted default {doctype}: {name}")
        except Exception as e:
            error_msg = str(e)
            # Non loggare warning per nodi NestedSet con figli (è normale)
            if "has child nodes" in error_msg:
                frappe.logger("solede_setup").debug(f"Skipped {doctype} {name}: is a parent node")
            else:
                frappe.logger("solede_setup").warning(f"Could not delete {doctype} {name}: {e}")


def _delete_company_tax_templates(company: str):
    """Elimina tutti i tax templates e gli account tax di una company."""
    # 1. Elimina i tax templates
    for doctype in ["Sales Taxes and Charges Template", "Purchase Taxes and Charges Template", "Item Tax Template"]:
        templates = frappe.get_all(doctype, filters={"company": company}, pluck="name")
        for name in templates:
            try:
                frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
                frappe.logger("solede_setup").info(f"Deleted {doctype}: {name}")
            except Exception as e:
                frappe.logger("solede_setup").warning(f"Could not delete {doctype} {name}: {e}")

    # 2. Elimina gli account tax creati automaticamente
    _delete_tax_accounts(company)


def _delete_tax_accounts(company: str):
    """Elimina gli account tax creati automaticamente (sotto Duties and Taxes)."""
    # Trova l'account "Duties and Taxes" per questa company
    duties_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_name": "Duties and Taxes"},
        "name"
    )

    if not duties_account:
        return

    # Trova tutti gli account figli di "Duties and Taxes"
    child_accounts = frappe.get_all(
        "Account",
        filters={"parent_account": duties_account, "company": company},
        pluck="name"
    )

    # Elimina prima i figli (VAT accounts)
    for account_name in child_accounts:
        try:
            frappe.delete_doc("Account", account_name, force=True, ignore_permissions=True)
            frappe.logger("solede_setup").info(f"Deleted tax account: {account_name}")
        except Exception as e:
            frappe.logger("solede_setup").warning(f"Could not delete account {account_name}: {e}")

    # Poi elimina il parent "Duties and Taxes"
    try:
        frappe.delete_doc("Account", duties_account, force=True, ignore_permissions=True)
        frappe.logger("solede_setup").info(f"Deleted tax account: {duties_account}")
    except Exception as e:
        frappe.logger("solede_setup").warning(f"Could not delete account {duties_account}: {e}")


def _delete_company_warehouses(company: str):
    """Elimina i warehouse default di una company (tranne All Warehouses)."""
    default_warehouse_names = ["Stores", "Work In Progress", "Finished Goods", "Goods In Transit"]

    # I warehouse hanno il nome con suffisso company abbreviation
    warehouses = frappe.get_all(
        "Warehouse",
        filters={"company": company},
        pluck="name"
    )

    for wh_name in warehouses:
        # Controlla se è un warehouse default (il nome inizia con uno dei default)
        is_default = any(wh_name.startswith(default) for default in default_warehouse_names)
        if is_default:
            try:
                frappe.delete_doc("Warehouse", wh_name, force=True, ignore_permissions=True)
                frappe.logger("solede_setup").info(f"Deleted Warehouse: {wh_name}")
            except Exception as e:
                frappe.logger("solede_setup").warning(f"Could not delete Warehouse {wh_name}: {e}")


def _apply_custom_templates(profile, company: str):
    """Applica template custom dal profilo."""
    templates = profile.get_custom_templates()

    # TODO: Implementare import da JSON per ogni tipo di template
    # Questo sarà fatto quando creeremo i DocType importer specifici
    for template_type, json_path in templates.items():
        if json_path:
            frappe.logger("solede_setup").info(
                f"Custom template {template_type}: {json_path} (import not yet implemented)"
            )


# ============================================================================
# DEFAULT DOCUMENT LISTS
# ============================================================================

def _get_default_item_groups() -> list:
    """Lista Item Groups default di ERPNext (escluso root node)."""
    return [
        # "All Item Groups" è il root node, non può essere eliminato
        "Products",
        "Raw Material",
        "Services",
        "Sub Assemblies",
        "Consumable",
    ]


def _get_default_territories() -> list:
    """Lista Territories default di ERPNext (escluso root node)."""
    return [
        # "All Territories" è il root node, non può essere eliminato
        "Rest Of The World",
        # Il territorio del paese viene mantenuto
    ]


def _get_default_customer_groups() -> list:
    """Lista Customer Groups default di ERPNext (escluso root node)."""
    return [
        # "All Customer Groups" è il root node, non può essere eliminato
        "Individual",
        "Commercial",
        "Non Profit",
        "Government",
    ]


def _get_default_supplier_groups() -> list:
    """Lista Supplier Groups default di ERPNext (escluso root node)."""
    return [
        # "All Supplier Groups" è il root node, non può essere eliminato
        "Services",
        "Local",
        "Raw Material",
        "Electrical",
        "Hardware",
        "Pharmaceutical",
        "Distributor",
    ]


def _get_default_mode_of_payment() -> list:
    """Lista Mode of Payment default di ERPNext."""
    return [
        "Cash",
        "Cheque",
        "Check",
        "Credit Card",
        "Wire Transfer",
        "Bank Draft",
    ]


def _get_default_stock_entry_types() -> list:
    """Lista Stock Entry Types default di ERPNext."""
    return [
        "Material Issue",
        "Material Receipt",
        "Material Transfer",
        "Manufacture",
        "Repack",
        "Disassemble",
        "Send to Subcontractor",
        "Material Transfer for Manufacture",
        "Material Consumption for Manufacture",
    ]


def _get_default_price_lists() -> list:
    """Lista Price Lists default di ERPNext."""
    return [
        "Standard Buying",
        "Standard Selling",
    ]


def before_wizard_stage(args):
    """
    Hook: setup_wizard_stages (custom stage)

    Aggiunge uno stage custom all'inizio del wizard per:
    - Abilitare il tracking
    - Verificare se esiste un Setup Profile da applicare

    Returns:
        Lista di stage da aggiungere al wizard
    """
    return [
        {
            "status": _("Solede Setup - Preparing"),
            "fail_msg": _("Failed to initialize Solede Setup"),
            "tasks": [
                {
                    "fn": _init_solede_tracking,
                    "args": args,
                    "fail_msg": _("Failed to initialize tracking")
                }
            ]
        }
    ]


def _init_solede_tracking(args):
    """Inizializza il tracking durante il wizard."""
    enable_tracking()
    frappe.logger("solede_setup").info("Solede Setup tracking enabled")


# ============================================================================
# DOCUMENT EVENT HOOKS
# ============================================================================

def on_account_after_insert(doc, method):
    """Intercetta creazione Account."""
    _on_doctype_created(doc, "Account")


def on_warehouse_after_insert(doc, method):
    """Intercetta creazione Warehouse."""
    _on_doctype_created(doc, "Warehouse")


def on_cost_center_after_insert(doc, method):
    """Intercetta creazione Cost Center."""
    _on_doctype_created(doc, "Cost Center")


def on_department_after_insert(doc, method):
    """Intercetta creazione Department."""
    _on_doctype_created(doc, "Department")


def on_item_group_after_insert(doc, method):
    """Intercetta creazione Item Group."""
    _on_doctype_created(doc, "Item Group")


def on_territory_after_insert(doc, method):
    """Intercetta creazione Territory."""
    _on_doctype_created(doc, "Territory")


def on_customer_group_after_insert(doc, method):
    """Intercetta creazione Customer Group."""
    _on_doctype_created(doc, "Customer Group")


def on_supplier_group_after_insert(doc, method):
    """Intercetta creazione Supplier Group."""
    _on_doctype_created(doc, "Supplier Group")


def on_sales_tax_template_after_insert(doc, method):
    """Intercetta creazione Sales Taxes and Charges Template."""
    _on_doctype_created(doc, "Sales Taxes and Charges Template")


def on_purchase_tax_template_after_insert(doc, method):
    """Intercetta creazione Purchase Taxes and Charges Template."""
    _on_doctype_created(doc, "Purchase Taxes and Charges Template")


def on_item_tax_template_after_insert(doc, method):
    """Intercetta creazione Item Tax Template."""
    _on_doctype_created(doc, "Item Tax Template")


def on_mode_of_payment_after_insert(doc, method):
    """Intercetta creazione Mode of Payment."""
    _on_doctype_created(doc, "Mode of Payment")


def on_price_list_after_insert(doc, method):
    """Intercetta creazione Price List."""
    _on_doctype_created(doc, "Price List")


def on_stock_entry_type_after_insert(doc, method):
    """Intercetta creazione Stock Entry Type."""
    _on_doctype_created(doc, "Stock Entry Type")


def on_uom_after_insert(doc, method):
    """Intercetta creazione UOM."""
    _on_doctype_created(doc, "UOM")


def on_payment_term_after_insert(doc, method):
    """Intercetta creazione Payment Term."""
    _on_doctype_created(doc, "Payment Term")


def on_payment_terms_template_after_insert(doc, method):
    """Intercetta creazione Payment Terms Template."""
    _on_doctype_created(doc, "Payment Terms Template")


def _on_doctype_created(doc, doctype: str):
    """
    Handler generico per intercettare la creazione di un DocType.

    Determina la sorgente della creazione e logga l'evento.
    """
    # Determina la sorgente
    source = _determine_creation_source(doc)

    # Logga la creazione
    log_creation(doctype, doc.name, source)

    # Log per debug
    if is_tracking_enabled():
        frappe.logger("solede_setup").debug(
            f"Intercepted {doctype} creation: {doc.name} (source: {source})"
        )


def _determine_creation_source(doc) -> str:
    """
    Determina la sorgente di creazione di un documento.

    Returns:
        - "erpnext_auto": Creato automaticamente da ERPNext durante setup
        - "solede_setup": Creato da solede_setup
        - "user": Creato manualmente dall'utente
    """
    # Se il tracking è attivo, probabilmente è durante il setup
    if is_tracking_enabled():
        return "erpnext_auto"

    # Se ha flag solede_setup, viene da noi
    if getattr(doc, "flags", {}).get("solede_setup_created"):
        return "solede_setup"

    # Altrimenti è creazione utente
    return "user"


# ============================================================================
# COMPANY HOOKS - Punto critico dove ERPNext crea molti dati automatici
# ============================================================================

def on_company_after_insert(doc, method):
    """
    Intercetta creazione Company.

    Quando una Company viene creata, ERPNext automaticamente crea:
    - Chart of Accounts (tutti gli Account)
    - Default Warehouses (Stores, Finished Goods, Work In Progress)
    - Default Cost Centers
    - Default Departments
    - Tax Templates (se country fixtures attive)

    Questo hook viene chiamato DOPO che Company.after_insert() di ERPNext
    ha già creato tutti questi documenti.
    """
    log_creation("Company", doc.name, "erpnext_auto")

    frappe.logger("solede_setup").info(
        f"Company created: {doc.name} - Country: {doc.country}"
    )

    # Salva metadata sul setup
    frappe.flags.solede_setup_company = doc.name
    frappe.flags.solede_setup_country = doc.country


def on_company_on_update(doc, method):
    """
    Intercetta update Company.

    Importante: quando country cambia, ERPNext chiama:
    - install_country_fixtures()
    - create_default_tax_template()
    """
    if frappe.flags.get("country_change"):
        frappe.logger("solede_setup").info(
            f"Company {doc.name} country changed - ERPNext will install country fixtures"
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_setup_log(company: str = None, doctype: str = None) -> list:
    """
    Recupera il log delle creazioni durante il setup.

    Args:
        company: Filtra per company (opzionale)
        doctype: Filtra per doctype (opzionale)

    Returns:
        Lista di dizionari con i log
    """
    filters = {}
    if doctype:
        filters["doctype_name"] = doctype

    try:
        logs = frappe.get_all(
            "Setup Log",
            filters=filters,
            fields=["doctype_name", "document_name", "source", "created_at"],
            order_by="created_at desc"
        )
        return logs
    except Exception:
        return []


def get_auto_created_documents(doctype: str) -> list:
    """
    Recupera i documenti creati automaticamente per un DocType.

    Args:
        doctype: Nome del DocType

    Returns:
        Lista di nomi documenti creati automaticamente
    """
    try:
        logs = frappe.get_all(
            "Setup Log",
            filters={
                "doctype_name": doctype,
                "source": "erpnext_auto"
            },
            pluck="document_name"
        )
        return logs
    except Exception:
        return []


def delete_auto_created(doctype: str, confirm: bool = False) -> dict:
    """
    Elimina tutti i documenti creati automaticamente per un DocType.

    Args:
        doctype: Nome del DocType
        confirm: Se True, esegue l'eliminazione

    Returns:
        Dizionario con conteggio e lista documenti
    """
    documents = get_auto_created_documents(doctype)

    result = {
        "doctype": doctype,
        "count": len(documents),
        "documents": documents,
        "deleted": False
    }

    if confirm and documents:
        deleted = 0
        for docname in documents:
            try:
                frappe.delete_doc(doctype, docname, force=True)
                deleted += 1
            except Exception as e:
                frappe.logger("solede_setup").error(
                    f"Failed to delete {doctype} {docname}: {e}"
                )

        result["deleted"] = True
        result["deleted_count"] = deleted

    return result
