"""
Override della classe Company per controllare gli automatismi di setup.

Quando è attivo un Setup Profile con skip_default_tax_templates=1,
il metodo create_default_tax_template() non viene eseguito.
"""

import frappe
from erpnext.setup.doctype.company.company import Company


class CustomCompany(Company):

    def create_default_tax_template(self):
        """
        Override: controlla Setup Profile prima di creare tax templates.
        """
        if self._should_skip_tax_templates():
            frappe.logger("solede_setup").info(
                f"Skipping tax template creation for {self.name} (Setup Profile active)"
            )
            return

        # Chiama il metodo originale
        super().create_default_tax_template()

    def _should_skip_tax_templates(self) -> bool:
        """Verifica se skippare la creazione dei tax templates."""
        try:
            profile = frappe.db.get_value(
                "Setup Profile",
                {"is_active": 1},
                "skip_default_tax_templates"
            )
            return bool(profile)
        except Exception:
            return False
