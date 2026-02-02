"""
Solede Setup - Bench Commands

Uso:
    bench --site [site] set-setup-profile "CH Clean Start"
    bench --site [site] list-setup-profiles
    bench --site [site] show-setup-profile "CH Clean Start"
"""

import click
import frappe
from frappe.commands import pass_context


@click.command("set-setup-profile")
@click.argument("profile_name")
@pass_context
def set_setup_profile(context, profile_name):
    """Attiva un Setup Profile per il prossimo Setup Wizard."""
    site = context.sites[0] if context.sites else None
    if not site:
        raise click.ClickException("Specifica il site con --site")

    frappe.init(site=site)
    frappe.connect()

    try:
        if not frappe.db.exists("Setup Profile", profile_name):
            available = frappe.get_all("Setup Profile", pluck="name")
            raise click.ClickException(
                f"Profile '{profile_name}' non trovato.\n"
                f"Profili disponibili: {', '.join(available)}"
            )

        # Disattiva tutti
        frappe.db.sql("UPDATE `tabSetup Profile` SET is_active = 0")

        # Attiva quello richiesto
        frappe.db.set_value("Setup Profile", profile_name, "is_active", 1)
        frappe.db.commit()

        click.echo(f"✓ Setup Profile '{profile_name}' attivato.")
        click.echo("  Ora esegui il Setup Wizard: i dati default verranno puliti automaticamente.")

    finally:
        frappe.destroy()


@click.command("list-setup-profiles")
@pass_context
def list_setup_profiles(context):
    """Elenca tutti i Setup Profile disponibili."""
    site = context.sites[0] if context.sites else None
    if not site:
        raise click.ClickException("Specifica il site con --site")

    frappe.init(site=site)
    frappe.connect()

    try:
        profiles = frappe.get_all(
            "Setup Profile",
            fields=["profile_name", "is_active", "description"],
            order_by="profile_name"
        )

        if not profiles:
            click.echo("Nessun Setup Profile trovato.")
            return

        click.echo("\nSetup Profiles:\n")
        for p in profiles:
            status = "→ " if p.is_active else "  "
            click.echo(f"{status}{p.profile_name}")
            if p.description:
                click.echo(f"    {p.description}")

    finally:
        frappe.destroy()


@click.command("show-setup-profile")
@click.argument("profile_name")
@pass_context
def show_setup_profile(context, profile_name):
    """Mostra dettagli di un Setup Profile."""
    site = context.sites[0] if context.sites else None
    if not site:
        raise click.ClickException("Specifica il site con --site")

    frappe.init(site=site)
    frappe.connect()

    try:
        if not frappe.db.exists("Setup Profile", profile_name):
            raise click.ClickException(f"Profile '{profile_name}' non trovato.")

        doc = frappe.get_doc("Setup Profile", profile_name)

        click.echo(f"\n{doc.profile_name}")
        click.echo(f"{'=' * len(doc.profile_name)}")
        click.echo(f"Stato: {'ATTIVO' if doc.is_active else 'non attivo'}")
        if doc.description:
            click.echo(f"{doc.description}\n")

        click.echo("Elimina:")
        skip_fields = [
            ("skip_default_item_groups", "Item Groups"),
            ("skip_default_territories", "Territories"),
            ("skip_default_customer_groups", "Customer Groups"),
            ("skip_default_supplier_groups", "Supplier Groups"),
            ("skip_default_mode_of_payment", "Mode of Payment"),
            ("skip_default_stock_entry_types", "Stock Entry Types"),
            ("skip_default_price_lists", "Price Lists"),
            ("skip_default_tax_templates", "Tax Templates"),
            ("skip_default_payment_terms", "Payment Terms"),
        ]

        for field, label in skip_fields:
            if getattr(doc, field, 0):
                click.echo(f"  ✓ {label}")

    finally:
        frappe.destroy()


commands = [
    set_setup_profile,
    list_setup_profiles,
    show_setup_profile,
]
