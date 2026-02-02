"""
Override Warehouse per supportare custom_id come nome documento.
"""

import frappe
from erpnext.stock.doctype.warehouse.warehouse import Warehouse


class CustomWarehouse(Warehouse):
    def autoname(self):
        """Se custom_id è valorizzato, usa quello + abbreviazione company."""
        if self.get("custom_id") and self.get("company"):
            company_abbr = frappe.get_cached_value("Company", self.company, "abbr")
            self.name = f"{self.custom_id} - {company_abbr}"
        else:
            # Comportamento originale di ERPNext
            super().autoname()
