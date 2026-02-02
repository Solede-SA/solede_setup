/**
 * Solede Setup - Setup Wizard Customization
 *
 * Modifica l'interfaccia del Setup Wizard per informare l'utente
 * quando è attivo un Setup Profile.
 */

frappe.provide("solede_setup");

solede_setup.setup_wizard = {

    init: function() {
        // Verifica se c'è un Setup Profile attivo
        this.check_active_profile();
    },

    check_active_profile: function() {
        frappe.call({
            method: "solede_setup.api.get_active_setup_profile",
            async: false,
            callback: (r) => {
                if (r.message) {
                    this.active_profile = r.message;
                    this.inject_warnings();
                }
            }
        });
    },

    inject_warnings: function() {
        const profile = this.active_profile;

        // Aspetta che il wizard sia caricato
        $(document).ready(() => {
            this.add_profile_banner(profile);
            this.modify_chart_of_accounts_step(profile);
        });

        // Hook sugli slide change per aggiungere avvisi dinamici
        if (frappe.setup) {
            const original_show_slide = frappe.setup.slides_progress?.show_slide;
            if (original_show_slide) {
                frappe.setup.slides_progress.show_slide = (slide_index) => {
                    original_show_slide.call(frappe.setup.slides_progress, slide_index);
                    this.on_slide_change(slide_index);
                };
            }
        }
    },

    add_profile_banner: function(profile) {
        // Aggiungi banner informativo in cima al wizard
        const banner_html = `
            <div class="solede-setup-banner" style="
                background: #e8f4fd;
                border: 1px solid #b8daff;
                border-radius: 4px;
                padding: 12px 16px;
                margin: 10px 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            ">
                <span style="font-size: 18px;">⚙️</span>
                <div>
                    <strong>Setup Profile attivo: ${profile.profile_name}</strong>
                    <br>
                    <small style="color: #666;">
                        ${profile.description || "I dati default verranno modificati dopo il wizard."}
                    </small>
                </div>
            </div>
        `;

        // Inserisci il banner
        setTimeout(() => {
            const wizard_container = $(".setup-wizard-slide, .frappe-control, .page-container").first();
            if (wizard_container.length && !$(".solede-setup-banner").length) {
                wizard_container.prepend(banner_html);
            }
        }, 500);
    },

    modify_chart_of_accounts_step: function(profile) {
        // Monitora quando appare il campo chart_of_accounts
        const observer = new MutationObserver((mutations) => {
            const coa_field = $('[data-fieldname="chart_of_accounts"]');
            if (coa_field.length && !coa_field.data("solede-modified")) {
                coa_field.data("solede-modified", true);
                this.add_coa_warning(coa_field, profile);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    },

    add_coa_warning: function(coa_field, profile) {
        const warning_html = `
            <div class="solede-coa-warning" style="
                background: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 4px;
                padding: 10px 14px;
                margin-top: 10px;
                margin-bottom: 20px;
                font-size: 13px;
            ">
                <strong>ℹ️ Nota:</strong> Puoi selezionare un piano dei conti qualsiasi.
                <br>
                Con il profilo <strong>"${profile.profile_name}"</strong> attivo,
                potrai sostituirlo con un piano dei conti personalizzato dopo il wizard.
            </div>
        `;

        coa_field.closest(".frappe-control").after(warning_html);
    },

    on_slide_change: function(slide_index) {
        // Rimuovi e riaggiungi il banner se necessario
        if (this.active_profile && !$(".solede-setup-banner").length) {
            this.add_profile_banner(this.active_profile);
        }
    }
};

// Inizializza quando il documento è pronto
$(document).ready(function() {
    // Verifica se siamo nel setup wizard
    if (frappe.setup_wizard || window.location.pathname.includes("setup-wizard")) {
        solede_setup.setup_wizard.init();
    }
});
