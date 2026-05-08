// Client Script — Marché KYA (Desk)

const COUT_FIELDS = [
    "cout_supports_pv", "cout_supports_batteries", "cout_modules_pv", "cout_batteries",
    "cout_onduleurs", "cout_cables", "cout_terre", "cout_protection",
    "cout_accessoires_cablage", "cout_gestionnaire",
    "frais_carburant", "frais_location_camion", "frais_perdiems",
    "frais_hebergement", "frais_autres",
];

function recompute(frm) {
    let total = 0;
    COUT_FIELDS.forEach(f => { total += flt(frm.doc[f] || 0); });
    frm.set_value("cout_total_realisation", total);

    const facture = flt(frm.doc.montant_total_facture || 0);
    const avance  = flt(frm.doc.montant_avance_demarrage || 0);
    const budget  = flt(frm.doc.budget_previsionnel || 0);
    const taxes   = flt(frm.doc.taxes || 0);

    frm.set_value("ecart_avance", total - avance);
    frm.set_value("ecart_budget_previsionnel", total - budget);
    const mb = facture - total;
    frm.set_value("marge_brute", mb);
    frm.set_value("marge_nette", mb - taxes);
}

function recompute_duree(frm) {
    if (frm.doc.date_debut && frm.doc.date_fin) {
        const debut = frappe.datetime.str_to_obj(frm.doc.date_debut);
        const fin   = frappe.datetime.str_to_obj(frm.doc.date_fin);
        const diff  = Math.round((fin - debut) / 86400000);
        frm.set_value("duree_jours", diff >= 0 ? diff : 0);
    }
}

const COUT_HANDLERS = {};
COUT_FIELDS.forEach(f => { COUT_HANDLERS[f] = recompute; });
COUT_HANDLERS["montant_total_facture"]    = recompute;
COUT_HANDLERS["montant_avance_demarrage"] = recompute;
COUT_HANDLERS["budget_previsionnel"]      = recompute;
COUT_HANDLERS["taxes"]                   = recompute;
COUT_HANDLERS["date_debut"]              = recompute_duree;
COUT_HANDLERS["date_fin"]               = recompute_duree;
COUT_HANDLERS["refresh"]                = recompute;

frappe.ui.form.on("Marche KYA", COUT_HANDLERS);
