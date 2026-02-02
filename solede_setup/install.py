"""
Solede Setup - Install Hooks

Questo modulo gestisce l'installazione dell'app:
- Crea profili di setup predefiniti
- Configura impostazioni iniziali
"""

import frappe


def after_install():
    """
    Eseguito dopo l'installazione dell'app.
    Crea i Setup Profile predefiniti.
    """
    create_default_profiles()
    frappe.db.commit()


def create_default_profiles():
    """Crea i profili di setup predefiniti."""

    profiles = [
        {
            "profile_name": "CH Clean Start",
            "description": "Profilo Svizzera: elimina tutti i dati default ERPNext per partire da zero",
            "is_active": 0,
            "skip_default_item_groups": 1,
            "skip_default_territories": 1,
            "skip_default_customer_groups": 1,
            "skip_default_supplier_groups": 1,
            "skip_default_mode_of_payment": 1,
            "skip_default_stock_entry_types": 0,
            "skip_default_price_lists": 1,
            "skip_default_uom": 0,
            "skip_default_warehouses": 1,
            "skip_default_tax_templates": 1,
            "skip_default_payment_terms": 1,
            "skip_country_fixtures": 0,
            "delete_demo_data": 1,
            "delete_sample_company": 1,
        },
        {
            "profile_name": "IT Clean Start",
            "description": "Profilo Italia: elimina dati default, mantiene country fixtures per fatturazione elettronica",
            "is_active": 0,
            "skip_default_item_groups": 1,
            "skip_default_territories": 1,
            "skip_default_customer_groups": 1,
            "skip_default_supplier_groups": 1,
            "skip_default_mode_of_payment": 1,
            "skip_default_stock_entry_types": 0,
            "skip_default_price_lists": 1,
            "skip_default_uom": 0,
            "skip_default_warehouses": 1,
            "skip_default_tax_templates": 1,
            "skip_default_payment_terms": 1,
            "skip_country_fixtures": 0,
            "delete_demo_data": 1,
            "delete_sample_company": 1,
        },
        {
            "profile_name": "Keep All Defaults",
            "description": "Mantiene tutti i dati default di ERPNext (nessuna pulizia)",
            "is_active": 0,
            "skip_default_item_groups": 0,
            "skip_default_territories": 0,
            "skip_default_customer_groups": 0,
            "skip_default_supplier_groups": 0,
            "skip_default_mode_of_payment": 0,
            "skip_default_stock_entry_types": 0,
            "skip_default_price_lists": 0,
            "skip_default_uom": 0,
            "skip_default_warehouses": 0,
            "skip_default_tax_templates": 0,
            "skip_default_payment_terms": 0,
            "skip_country_fixtures": 0,
            "delete_demo_data": 0,
            "delete_sample_company": 0,
        },
    ]

    for profile_data in profiles:
        if not frappe.db.exists("Setup Profile", profile_data["profile_name"]):
            doc = frappe.get_doc({
                "doctype": "Setup Profile",
                **profile_data
            })
            doc.insert(ignore_permissions=True)
            frappe.logger("solede_setup").info(f"Created Setup Profile: {profile_data['profile_name']}")
