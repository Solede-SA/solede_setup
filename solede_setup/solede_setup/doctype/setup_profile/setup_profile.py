"""
Setup Profile - Configura cosa skippare/modificare durante il setup ERPNext.

Un Setup Profile permette di:
1. Skippare la creazione di dati default (Item Groups, Territories, ecc.)
2. Configurare pulizia post-setup
3. Eseguire cleanup completo dei dati master

Il profilo attivo viene letto durante il setup wizard per determinare
quali automatismi ERPNext bloccare o modificare.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class SetupProfile(Document):
    def validate(self):
        # Se questo profilo è attivo, disattiva gli altri
        if self.is_active:
            frappe.db.set_value(
                "Setup Profile",
                {"name": ["!=", self.name], "is_active": 1},
                "is_active",
                0
            )

    @staticmethod
    def get_active() -> "SetupProfile | None":
        """Recupera il profilo attivo."""
        name = frappe.db.get_value("Setup Profile", {"is_active": 1}, "name")
        if name:
            return frappe.get_doc("Setup Profile", name)
        return None

    @staticmethod
    def should_skip(setting: str) -> bool:
        """
        Verifica se un'impostazione deve essere skippata.

        Args:
            setting: Nome del campo (es. "skip_default_item_groups")

        Returns:
            True se deve essere skippato
        """
        profile = SetupProfile.get_active()
        if not profile:
            return False
        return bool(getattr(profile, setting, False))

    def get_skip_settings(self) -> dict:
        """Ritorna dizionario con tutte le impostazioni di skip."""
        return {
            "item_groups": self.skip_default_item_groups,
            "territories": self.skip_default_territories,
            "customer_groups": self.skip_default_customer_groups,
            "supplier_groups": self.skip_default_supplier_groups,
            "mode_of_payment": self.skip_default_mode_of_payment,
            "stock_entry_types": self.skip_default_stock_entry_types,
            "price_lists": self.skip_default_price_lists,
            "uom": self.skip_default_uom,
            "tax_templates": self.skip_default_tax_templates,
            "payment_terms": self.skip_default_payment_terms,
            "country_fixtures": self.skip_country_fixtures,
        }


def get_active_profile() -> "SetupProfile | None":
    """Helper function per recuperare il profilo attivo."""
    return SetupProfile.get_active()


def should_skip(setting: str) -> bool:
    """Helper function per verificare se skippare un'impostazione."""
    return SetupProfile.should_skip(setting)


@frappe.whitelist()
def cleanup_all_data(company: str) -> dict:
    """
    Cleanup completo dei dati master per una company.

    Elimina:
    - GL Entry
    - Stock Ledger Entry
    - Cost Centers
    - Warehouses
    - Tax Templates (Sales, Purchase, Item)
    - Accounts (opzionale, dopo GL cleanup)

    Args:
        company: Nome della company

    Returns:
        dict con risultato e conteggi
    """
    if not company:
        frappe.throw(_("Please select a Company"))

    results = {
        "company": company,
        "deleted": {}
    }

    # 1. Delete GL Entry
    count = frappe.db.count("GL Entry", {"company": company})
    if count:
        frappe.db.delete("GL Entry", {"company": company})
        results["deleted"]["GL Entry"] = count

    # 2. Delete Stock Ledger Entry
    count = frappe.db.count("Stock Ledger Entry", {"company": company})
    if count:
        frappe.db.delete("Stock Ledger Entry", {"company": company})
        results["deleted"]["Stock Ledger Entry"] = count

    # 3. Delete Cost Centers (in reverse lft order)
    cost_centers = frappe.get_all(
        "Cost Center",
        filters={"company": company},
        order_by="lft desc",
        pluck="name"
    )
    for name in cost_centers:
        try:
            frappe.delete_doc("Cost Center", name, ignore_permissions=True, force=True)
        except Exception:
            pass
    if cost_centers:
        results["deleted"]["Cost Center"] = len(cost_centers)

    # 4. Delete Warehouses (in reverse lft order)
    warehouses = frappe.get_all(
        "Warehouse",
        filters={"company": company},
        order_by="lft desc",
        pluck="name"
    )
    for name in warehouses:
        try:
            frappe.delete_doc("Warehouse", name, ignore_permissions=True, force=True)
        except Exception:
            pass
    if warehouses:
        results["deleted"]["Warehouse"] = len(warehouses)

    # 5. Delete Sales Tax Templates
    templates = frappe.get_all(
        "Sales Taxes and Charges Template",
        filters={"company": company},
        pluck="name"
    )
    for name in templates:
        frappe.delete_doc("Sales Taxes and Charges Template", name, ignore_permissions=True, force=True)
    if templates:
        results["deleted"]["Sales Taxes and Charges Template"] = len(templates)

    # 6. Delete Purchase Tax Templates
    templates = frappe.get_all(
        "Purchase Taxes and Charges Template",
        filters={"company": company},
        pluck="name"
    )
    for name in templates:
        frappe.delete_doc("Purchase Taxes and Charges Template", name, ignore_permissions=True, force=True)
    if templates:
        results["deleted"]["Purchase Taxes and Charges Template"] = len(templates)

    # 7. Delete Item Tax Templates
    templates = frappe.get_all(
        "Item Tax Template",
        filters={"company": company},
        pluck="name"
    )
    for name in templates:
        frappe.delete_doc("Item Tax Template", name, ignore_permissions=True, force=True)
    if templates:
        results["deleted"]["Item Tax Template"] = len(templates)

    # 8. Delete Mode of Payment Accounts for this company
    # (Mode of Payment is global, but accounts are per company)
    mop_accounts = frappe.get_all(
        "Mode of Payment Account",
        filters={"company": company},
        pluck="name"
    )
    for name in mop_accounts:
        frappe.delete_doc("Mode of Payment Account", name, ignore_permissions=True, force=True)
    if mop_accounts:
        results["deleted"]["Mode of Payment Account"] = len(mop_accounts)

    frappe.db.commit()

    return results


@frappe.whitelist()
def cleanup_global_data() -> dict:
    """
    Cleanup dei dati globali (non legati a company).

    Elimina:
    - Item Groups (eccetto root)
    - Territories (eccetto root)
    - Customer Groups (eccetto root)
    - Supplier Groups (eccetto root)
    - Mode of Payment
    - Payment Terms

    Returns:
        dict con risultato e conteggi
    """
    results = {"deleted": {}}

    # Helper per eliminare NestedSet in ordine corretto
    def delete_nested_set(doctype: str, root_name: str = None):
        items = frappe.get_all(
            doctype,
            order_by="lft desc",
            pluck="name"
        )
        count = 0
        for name in items:
            # Skip root node
            if root_name and name == root_name:
                continue
            try:
                frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
                count += 1
            except Exception:
                pass
        return count

    # 1. Item Groups
    count = delete_nested_set("Item Group", "All Item Groups")
    if count:
        results["deleted"]["Item Group"] = count

    # 2. Territories
    count = delete_nested_set("Territory", "All Territories")
    if count:
        results["deleted"]["Territory"] = count

    # 3. Customer Groups
    count = delete_nested_set("Customer Group", "All Customer Groups")
    if count:
        results["deleted"]["Customer Group"] = count

    # 4. Supplier Groups
    count = delete_nested_set("Supplier Group", "All Supplier Groups")
    if count:
        results["deleted"]["Supplier Group"] = count

    # 5. Mode of Payment
    items = frappe.get_all("Mode of Payment", pluck="name")
    for name in items:
        try:
            frappe.delete_doc("Mode of Payment", name, ignore_permissions=True, force=True)
        except Exception:
            pass
    if items:
        results["deleted"]["Mode of Payment"] = len(items)

    # 6. Payment Terms
    items = frappe.get_all("Payment Term", pluck="name")
    for name in items:
        try:
            frappe.delete_doc("Payment Term", name, ignore_permissions=True, force=True)
        except Exception:
            pass
    if items:
        results["deleted"]["Payment Term"] = len(items)

    frappe.db.commit()

    return results
