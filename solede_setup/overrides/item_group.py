"""
Override Item Group per supportare custom_id come nome documento.
"""

from erpnext.setup.doctype.item_group.item_group import ItemGroup


class CustomItemGroup(ItemGroup):
    def autoname(self):
        """Se custom_id è valorizzato, usa quello come nome."""
        if self.get("custom_id"):
            self.name = self.custom_id
        else:
            # Comportamento originale di ERPNext
            super().autoname()
