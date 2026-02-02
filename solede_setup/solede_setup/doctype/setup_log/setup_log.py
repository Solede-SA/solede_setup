"""
Setup Log - Traccia i documenti creati durante il setup di ERPNext.

Questo DocType registra automaticamente:
- Quale DocType è stato creato
- Il nome del documento
- La sorgente (erpnext_auto, solede_setup, user)
- Quando è stato creato

Permette di:
- Vedere cosa è stato creato automaticamente
- Identificare documenti da pulire
- Tracciare le modifiche del setup
"""

import frappe
from frappe.model.document import Document


class SetupLog(Document):
    def before_insert(self):
        if not self.created_at:
            self.created_at = frappe.utils.now()

        if not self.company:
            self.company = frappe.flags.get("solede_setup_company")

    @staticmethod
    def log(doctype: str, docname: str, source: str = "erpnext_auto", company: str = None):
        """
        Crea un log entry.

        Args:
            doctype: Nome del DocType
            docname: Nome del documento creato
            source: Sorgente (erpnext_auto, solede_setup, user)
            company: Company associata (opzionale)
        """
        try:
            doc = frappe.get_doc({
                "doctype": "Setup Log",
                "doctype_name": doctype,
                "document_name": docname,
                "source": source,
                "company": company or frappe.flags.get("solede_setup_company"),
                "can_delete": 1
            })
            doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.logger("solede_setup").error(f"Failed to log {doctype}/{docname}: {e}")

    @staticmethod
    def get_auto_created(doctype: str = None, company: str = None) -> list:
        """
        Recupera documenti creati automaticamente.

        Args:
            doctype: Filtra per DocType (opzionale)
            company: Filtra per Company (opzionale)

        Returns:
            Lista di log entries
        """
        filters = {"source": "erpnext_auto"}
        if doctype:
            filters["doctype_name"] = doctype
        if company:
            filters["company"] = company

        return frappe.get_all(
            "Setup Log",
            filters=filters,
            fields=["doctype_name", "document_name", "created_at", "can_delete"],
            order_by="created_at desc"
        )
