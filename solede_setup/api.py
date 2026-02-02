"""
Solede Setup - API Endpoints

Endpoints per il frontend (Setup Wizard, ecc.)
"""

import frappe


@frappe.whitelist(allow_guest=True)
def get_active_setup_profile():
    """
    Ritorna il Setup Profile attivo, se presente.

    Chiamato dal Setup Wizard per mostrare avvisi all'utente.

    Returns:
        dict | None: Dati del profilo attivo o None
    """
    try:
        profile = frappe.db.get_value(
            "Setup Profile",
            {"is_active": 1},
            ["profile_name", "description",
             "skip_default_item_groups", "skip_default_territories",
             "skip_default_customer_groups", "skip_default_supplier_groups",
             "skip_default_tax_templates", "skip_default_price_lists"],
            as_dict=True
        )
        return profile
    except Exception:
        # Se il DocType non esiste ancora, ritorna None
        return None
