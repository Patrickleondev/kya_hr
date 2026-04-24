/* ===================================================================
   KYA-Energy Group â€” Web Form Layout v4
   Design : Ordre de Mission / Fiche officielle KYA
   En-tête 2-colonnes : Logo gauche | Titre + infos droite
   NÂ° de document affiché, sections numérotées,
   permissions par rôle, signatures verrouillées.
   =================================================================== */

/* === Auto-redirect bare web form URLs to /new ==================== */
(function () {
  var KYA_WF_ROUTES = [
    "permission-sortie-stagiaire", "permission-sortie-employe",
    "demande-achat", "demande-conge", "pv-sortie-materiel",
    "planning-conge", "bilan-fin-de-stage",
    "pv-entree-materiel",
    "brouillard-caisse", "etat-recap", "bon-commande",
    "appel-offre"
  ];
  var path = window.location.pathname.replace(/^\//, "").replace(/\/$/, "");
  var pathParts = path.split("/");
  var params = new URLSearchParams(window.location.search || "");
  var hasDocPointer = params.has("name") || params.has("docname") || params.has("id");

  // Normalize legacy links like /permission-sortie-employe/PSE-2026-00001
  if (pathParts.length === 2 && KYA_WF_ROUTES.indexOf(pathParts[0]) !== -1 && pathParts[1] !== "new") {
    if (!params.has("name")) {
      params.set("name", pathParts[1]);
    }
    window.location.replace("/" + pathParts[0] + "?" + params.toString());
    return;
  }

  if (KYA_WF_ROUTES.indexOf(path) !== -1 && !hasDocPointer) {
    // Bare route without /new â€” redirect silently
    window.location.replace("/" + path + "/new");
    return; // stop further execution until redirect completes
  }
})();

(function () {
  "use strict";

  var FORM_SECTIONS = {
    "permission-sortie-stagiaire": [
      {
        title: "IDENTIFICATION DU STAGIAIRE",
        icon: "\u{1F464}",
        fields: ["employee", "employee_name", "department"],
        grid: { employee: "span 2", employee_name: "col", department: "col" }
      },
      {
        title: "D\u00c9TAILS DE LA SORTIE",
        icon: "\u{1F6AA}",
        fields: ["date_sortie", "date_fin", "nombre_jours", "heure_depart", "heure_retour", "motif", "justificatif"],
        grid: {
          date_sortie: "col", date_fin: "col", nombre_jours: "col",
          heure_depart: "col", heure_retour: "col",
          motif: "span 2", justificatif: "span 2"
        }
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_stagiaire", "signature_chef", "signature_resp_stagiaires", "signature_dg"],
        sigGrid: true
      }
    ],
    "permission-sortie-employe": [
      {
        title: "IDENTIFICATION DE L\u2019EMPLOY\u00c9",
        icon: "\u{1F464}",
        fields: ["employee", "employee_name", "department"],
        grid: { employee: "span 2", employee_name: "col", department: "col" }
      },
      {
        title: "D\u00c9TAILS DE LA SORTIE",
        icon: "\u{1F6AA}",
        fields: ["date_sortie", "heure_depart", "heure_retour", "motif", "justificatif"],
        grid: {
          date_sortie: "col", heure_depart: "col", heure_retour: "col",
          motif: "span 2", justificatif: "span 2"
        }
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_employe", "signature_chef", "signature_rh", "signature_dga"],
        sigGrid: true
      }
    ],
    "demande-achat": [
      {
        title: "IDENTIFICATION DU DEMANDEUR",
        icon: "\u{1F464}",
        fields: ["employee", "employee_name", "department"],
        grid: { employee: "span 2", employee_name: "col", department: "col" }
      },
      {
        title: "D\u00c9TAILS DE LA DEMANDE",
        icon: "\u{1F4CB}",
        fields: ["date_demande", "objet", "urgence"],
        grid: { date_demande: "col", urgence: "col", objet: "span 2" }
      },
      {
        title: "ARTICLES DEMAND\u00c9S",
        icon: "\u{1F6D2}",
        fields: ["items", "montant_total"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_demandeur", "signature_chef", "signature_dga", "signature_dg"],
        sigGrid: true
      }
    ],
    "demande-conge": [
      {
        title: "IDENTIFICATION DE L\u2019EMPLOY\u00c9",
        icon: "\u{1F464}",
        fields: ["employee", "employee_name", "department"],
        grid: { employee: "span 2", employee_name: "col", department: "col" }
      },
      {
        title: "D\u00c9TAILS DU CONG\u00c9",
        icon: "\u{1F4C5}",
        fields: ["leave_type", "from_date", "to_date", "posting_date", "description"],
        grid: {
          leave_type: "col", from_date: "col", to_date: "col", posting_date: "col",
          description: "span 2"
        }
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_employe_la", "signature_superieur_la", "signature_rh_la", "signature_dg_la"],
        sigGrid: true
      }
    ],
    "pv-sortie-materiel": [
      {
        title: "INFORMATIONS DE LA SORTIE",
        icon: "\u{1F4E6}",
        fields: ["objet", "date_sortie"],
        grid: { objet: "span 2", date_sortie: "span 2" }
      },
      {
        title: "LISTE DU MAT\u00c9RIEL",
        icon: "\u{1F4DD}",
        fields: ["items", "demandeur_nom"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_demandeur", "signature_chef", "signature_audit", "signature_dga", "signature_magasin"],
        sigGrid: true
      }
    ],
    "pv-entree-materiel": [
      {
        title: "INFORMATIONS DE L\u2019ENTR\u00c9E",
        icon: "\u{1F4E5}",
        fields: ["objet", "date_entree", "fournisseur", "fournisseur_libre", "purchase_order"],
        grid: {
          objet: "span 2", date_entree: "col", fournisseur: "col",
          fournisseur_libre: "span 2", purchase_order: "span 2"
        }
      },
      {
        title: "ARTICLES RE\u00c7US",
        icon: "\u{1F4E6}",
        fields: ["items", "livreur_nom"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_livreur", "signature_magasin"],
        sigGrid: true
      }
    ],
    "inventaire-kya": [
      {
        title: "INFORMATIONS DE L\u2019INVENTAIRE",
        icon: "\u{1F4CB}",
        fields: ["objet", "date_inventaire", "type_inventaire", "warehouse_filter"],
        grid: { objet: "span 2", date_inventaire: "col", type_inventaire: "col", warehouse_filter: "span 2" }
      },
      {
        title: "LIGNES D\u2019INVENTAIRE",
        icon: "\u{1F4CA}",
        fields: ["items", "responsable_nom"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_responsable", "signature_magasin"],
        sigGrid: true
      }
    ],
    "planning-conge": [
      {
        title: "IDENTIFICATION DE L\u2019EMPLOY\u00c9",
        icon: "\u{1F464}",
        fields: ["employee", "employee_name", "department"],
        grid: { employee: "span 2", employee_name: "col", department: "col" }
      },
      {
        title: "PLANNING ANNUEL",
        icon: "\u{1F4C5}",
        fields: ["annee", "periodes"]
      },
      {
        title: "COMMENTAIRE",
        icon: "\u{1F4AC}",
        fields: ["commentaire_employe"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_employe", "signature_rh", "signature_dg"],
        sigGrid: true
      }
    ],
    "bilan-fin-de-stage": [
      {
        title: "IDENTIFICATION DU STAGIAIRE",
        icon: "\u{1F464}",
        fields: ["employee", "employee_name", "department", "encadrant"],
        grid: { employee: "col", employee_name: "col", department: "col", encadrant: "col" }
      },
      {
        title: "P\u00c9RIODE DE STAGE",
        icon: "\u{1F4C5}",
        fields: ["date_debut", "date_fin"],
        grid: { date_debut: "col", date_fin: "col" }
      },
      {
        title: "\u00c9VALUATION / BILAN",
        icon: "\u{1F4DD}",
        fields: ["evaluation"]
      },
      {
        title: "R\u00c9SULTATS",
        icon: "\u{1F3C6}",
        fields: ["note_globale", "mention"],
        grid: { note_globale: "col", mention: "col" }
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_stagiaire", "signature_encadrant", "signature_resp_stagiaires"],
        sigGrid: true
      }
    ],
    "brouillard-caisse": [
      {
        title: "IDENTIFICATION DE LA CAISSE",
        icon: "\u{1F4B0}",
        fields: ["date_brouillard", "caissiere", "caissiere_name", "solde_precedent", "date_solde_precedent"],
        grid: {
          date_brouillard: "col", caissiere: "col", caissiere_name: "col",
          solde_precedent: "col", date_solde_precedent: "col"
        }
      },
      {
        title: "OP\u00c9RATIONS DU JOUR",
        icon: "\u{1F4DD}",
        fields: ["lignes"]
      },
      {
        title: "TOTAUX & COMPTAGE",
        icon: "\u{1F4CA}",
        fields: ["total_entrees", "total_sorties", "solde_final", "total_reel_caisse", "commentaires"],
        grid: {
          total_entrees: "col", total_sorties: "col", solde_final: "col",
          total_reel_caisse: "col", commentaires: "span 2"
        }
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_caissiere", "signature_comptable", "signature_dfc"],
        sigGrid: true
      }
    ],
    "etat-recap": [
      {
        title: "IDENTIFICATION DE L\u2019\u00c9TAT",
        icon: "\u{1F4C4}",
        fields: ["date_etat", "redacteur", "redacteur_name", "semaine_du", "semaine_au"],
        grid: {
          date_etat: "col", redacteur: "col", redacteur_name: "col",
          semaine_du: "col", semaine_au: "col"
        }
      },
      {
        title: "CH\u00c8QUES \u00c9MIS",
        icon: "\u{1F4DD}",
        fields: ["lignes", "total_montant", "nombre_cheques", "commentaires"],
        grid: {
          lignes: "span 2", total_montant: "col", nombre_cheques: "col",
          commentaires: "span 2"
        }
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_redacteur", "signature_dfc", "signature_dg", "signature_dga"],
        sigGrid: true
      }
    ],
    "bon-commande": [
      {
        title: "IDENTIFICATION DU BON DE COMMANDE",
        icon: "\u{1F4E6}",
        fields: ["numero_bc", "date_bc", "demande_achat", "objet"],
        grid: { numero_bc: "col", date_bc: "col", demande_achat: "span 2", objet: "span 2" }
      },
      {
        title: "FOURNISSEUR",
        icon: "\u{1F3EA}",
        fields: ["fournisseur", "fournisseur_nom", "fournisseur_entreprise", "fournisseur_adresse", "fournisseur_ville", "fournisseur_telephone", "fournisseur_email"],
        grid: {
          fournisseur: "span 2",
          fournisseur_nom: "col", fournisseur_entreprise: "col",
          fournisseur_adresse: "span 2",
          fournisseur_ville: "col", fournisseur_telephone: "col",
          fournisseur_email: "span 2"
        }
      },
      {
        title: "ARTICLES COMMAND\u00c9S",
        icon: "\u{1F6D2}",
        fields: ["articles"]
      },
      {
        title: "TOTAUX & R\u00c8GLEMENT",
        icon: "\u{1F4B0}",
        fields: ["remise", "tva_taux", "modalites_paiement", "reglement"],
        grid: { remise: "col", tva_taux: "col", modalites_paiement: "span 2", reglement: "span 2" }
      },
      {
        title: "LIVRAISON & GARANTIE",
        icon: "\u{1F69A}",
        fields: ["delai_livraison", "lieu_livraison", "validite", "garantie"],
        grid: { delai_livraison: "col", lieu_livraison: "col", validite: "col", garantie: "col" }
      },
      {
        title: "AUTORISATION & SIGNATURE",
        icon: "\u270D\uFE0F",
        fields: ["autorise_par_nom", "autorise_par_fonction", "date_autorisation", "signature_dg"],
        sigGrid: true
      }
    ],
    "appel-offre": [
      {
        title: "IDENTIFICATION DE L\u2019APPEL D\u2019OFFRE",
        icon: "\u{1F4C4}",
        fields: ["date_ao", "date_limite", "demandeur", "demandeur_name", "service"],
        grid: {
          date_ao: "col", date_limite: "col",
          demandeur: "col", demandeur_name: "col",
          service: "span 2"
        }
      },
      {
        title: "OBJET",
        icon: "\u{1F4DD}",
        fields: ["objet", "demande_achat"],
        grid: { objet: "span 2", demande_achat: "span 2" }
      },
      {
        title: "ARTICLES / SERVICES DEMAND\u00c9S",
        icon: "\u{1F6D2}",
        fields: ["items"]
      },
      {
        title: "FOURNISSEURS CONSULT\u00c9S",
        icon: "\u{1F3EA}",
        fields: ["fournisseurs"]
      },
      {
        title: "MODALIT\u00c9S & CRIT\u00c8RES",
        icon: "\u{1F4CB}",
        fields: ["modalites", "criteres_selection", "message_fournisseur"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_demandeur", "signature_daaf", "signature_dg"],
        sigGrid: true
      }
    ]
  };

  var FORM_META = {
    "permission-sortie-stagiaire": {
      title: "DEMANDE DE PERMISSION DE SORTIE",
      subtitle: "Stagiaire",
      ref: "KYA-RH-PSS-V01",
      workflow: "Ma\u00eetre de Stage \u2192 Resp. Stagiaires \u2192 Direction"
    },
    "permission-sortie-employe": {
      title: "DEMANDE DE PERMISSION DE SORTIE",
      subtitle: "Employ\u00e9",
      ref: "KYA-RH-PSE-V01",
      workflow: "Chef de Service \u2192 RH \u2192 Direction"
    },
    "demande-achat": {
      title: "FICHE D\u2019ENGAGEMENT DE D\u00c9PENSES",
      subtitle: "Achats et Stocks",
      ref: "KYA-ACH-FED-V01",
      workflow: "Chef \u2192 Auditeur \u2192 DAAF \u2192 DG"
    },
    "demande-conge": {
      title: "DEMANDE DE CONG\u00c9",
      subtitle: "Ressources Humaines",
      ref: "KYA-RH-CNG-V01",
      workflow: "Sup. Imm\u00e9diat / Chef de Service \u2192 RH \u2192 DG"
    },
    "pv-sortie-materiel": {
      title: "PV DE SORTIE DE MAT\u00c9RIEL",
      subtitle: "Achats et Stocks",
      ref: "KYA-STK-PVM-V01",
      workflow: "Chef \u2192 Audit \u2192 Direction \u2192 Magasin"
    },
    "pv-entree-materiel": {
      title: "PV D\u2019ENTR\u00c9E DE MAT\u00c9RIEL",
      subtitle: "Achats et Stocks",
      ref: "KYA-STK-PEM-V01",
      workflow: "Livreur \u2192 Responsable Magasin"
    },
    "planning-conge": {
      title: "PLANNING DE CONG\u00c9 ANNUEL",
      subtitle: "Ressources Humaines",
      ref: "KYA-RH-PLN-V01",
      workflow: "Employ\u00e9 \u2192 RH \u2192 DG"
    },
    "bilan-fin-de-stage": {
      title: "BILAN DE FIN DE STAGE",
      subtitle: "Formation & Stages",
      ref: "KYA-RH-BFS-V01",
      workflow: "Stagiaire \u2192 Encadrant \u2192 RH"
    },
    "bon-commande": {
      title: "BON DE COMMANDE",
      subtitle: "Achats et Stocks",
      ref: "KYA-ACH-BC-V01",
      workflow: "Demandeur \u2192 DAAF \u2192 Direction G\u00e9n\u00e9rale \u2192 Fournisseur"
    },
    "brouillard-caisse": {
      title: "BROUILLARD DE CAISSE",
      subtitle: "Comptabilit\u00e9",
      ref: "KYA-CPT-BC-V01",
      workflow: "Caissier(\u00e8re) \u2192 Comptable \u2192 DFC"
    },
    "etat-recap": {
      title: "\u00c9TAT R\u00c9CAPITULATIF DES CH\u00c8QUES",
      subtitle: "Comptabilit\u00e9",
      ref: "KYA-CPT-ER-V01",
      workflow: "R\u00e9dacteur \u2192 DFC \u2192 DG / DGA"
    },
    "appel-offre": {
      title: "APPEL D\u2019OFFRE",
      subtitle: "Achats et Stocks",
      ref: "KYA-ACH-AO-V01",
      workflow: "Demandeur \u2192 DAAF \u2192 DG \u2192 Fournisseurs"
    }
  };

  /* Signature -> role mapping */
  var SIGNATURE_ROLES = {
    "permission-sortie-stagiaire": {
      signature_stagiaire: null,
      signature_chef: ["Chef Service", "HR Manager", "System Manager"],
      signature_resp_stagiaires: ["HR Manager", "HR User", "System Manager"],
      signature_dg: ["DG", "System Manager"]
    },
    "permission-sortie-employe": {
      signature_employe: null,
      signature_chef: ["Chef Service", "HR Manager", "System Manager"],
      signature_rh: ["HR Manager", "HR User", "System Manager"],
      signature_dga: ["DGA", "DG", "System Manager"]
    },
    "demande-achat": {
      signature_demandeur: null,
      signature_chef: ["Chef Service", "System Manager"],
      signature_dga: ["DGA", "DG", "System Manager"],
      signature_dg: ["DG", "System Manager"]
    },
    "pv-sortie-materiel": {
      signature_demandeur: null,
      signature_chef: ["Chef Service", "System Manager"],
      signature_audit: ["Auditeur Interne", "System Manager"],
      signature_dga: ["Directeur Général", "System Manager"],
      signature_magasin: ["Chargé des Stocks", "Stock Manager", "Stock User", "System Manager"]
    },
    "pv-entree-materiel": {
      signature_livreur: null,
      signature_magasin: ["Chargé des Stocks", "Responsable Stock", "Stock Manager", "Stock User", "System Manager"]
    },
    "inventaire-kya": {
      signature_responsable: null,
      signature_magasin: ["Chargé des Stocks", "Responsable Stock", "Stock Manager", "Stock User", "System Manager"]
    },
    "planning-conge": {
      signature_employe: null,
      signature_rh: ["Responsable RH", "HR Manager", "HR User", "System Manager"],
      signature_dg: ["Directeur Général", "System Manager"]
    },
    "bilan-fin-de-stage": {
      signature_stagiaire: null,
      signature_encadrant: ["Maître de Stage", "Responsable des Stagiaires", "System Manager"],
      signature_resp_stagiaires: ["Responsable des Stagiaires", "HR Manager", "System Manager"]
    },
    "brouillard-caisse": {
      signature_caissiere: null,
      signature_comptable: ["Comptable", "Accounts Manager", "Accounts User", "System Manager"],
      signature_dfc: ["DFC", "DAAF", "Accounts Manager", "System Manager"]
    },
    "etat-recap": {
      signature_redacteur: null,
      signature_dfc: ["DFC", "DAAF", "Accounts Manager", "System Manager"]
    },
    "bon-commande": {
      signature_dg: ["DG", "Directeur Général", "System Manager"]
    },
    "appel-offre": {
      signature_demandeur: null,
      signature_daaf: ["DAAF", "Purchase Manager", "System Manager"],
      signature_dg: ["DG", "Directeur Général", "System Manager"]
    }
  };

  var EDITOR_ROLES = [
    "HR Manager", "HR User", "System Manager",
    "DG", "DGA", "Chef Service", "Stock Manager"
  ];

  function getRoute() {
    if (window.frappe && frappe.web_form_doc && frappe.web_form_doc.route) {
      return frappe.web_form_doc.route;
    }
    var path = window.location.pathname.replace(/^\//, "").replace(/\/$/, "");
    return path.replace(/\/new$/, "").replace(/\/[^/]+$/, "");
  }

  function setLoadingState(isLoading) {
    var route = getRoute();
    if (!FORM_SECTIONS[route] && !FORM_META[route]) return;
    if (isLoading) document.body.classList.add("kya-wf-loading");
    else document.body.classList.remove("kya-wf-loading");
  }

  function injectVisibilityPatchCss() {
    if (document.getElementById("kya-wf-visibility-patch")) return;

    var style = document.createElement("style");
    style.id = "kya-wf-visibility-patch";
    style.textContent = [
      '/* Nuclear visibility fix â€” inline <style> injected by kya_webform.js */',
      'select, select option { color: #1a1a2e !important; -webkit-text-fill-color: #1a1a2e !important; background-color: #fff !important; }',
      '.grid-heading-row, .grid-heading-row * { color: #1a1a2e !important; -webkit-text-fill-color: #1a1a2e !important; background: #eaf2f8 !important; }',
      '.grid-heading-row .static-area { color: #1a1a2e !important; font-weight: 700 !important; font-size: 11px !important; }',
      '.grid-heading-row .col, .grid-heading-row [data-fieldname] { color: #1a1a2e !important; opacity: 1 !important; }',
      '.rows *, .grid-row *, .no-value, .grid-body * { color: #1a1a2e !important; -webkit-text-fill-color: #1a1a2e !important; }',
      '.frappe-control[data-fieldtype="Signature"] .signature-field { min-height: 160px !important; height: 160px !important; }',
      '.frappe-control[data-fieldtype="Signature"] .signature-pad, .frappe-control[data-fieldtype="Signature"] canvas { min-height: 160px !important; height: 160px !important; max-height: 160px !important; }',
      '.frappe-control[data-fieldtype="Signature"] .signature-display img { max-height: 160px !important; max-width: 100% !important; height: auto !important; width: auto !important; object-fit: contain !important; }',
    ].join('\n');

    document.head.appendChild(style);

    /* Also force inline styles on already-rendered elements */
    forceInlineTextVisibility();
  }

  function forceInlineTextVisibility() {
    /* Select elements */
    document.querySelectorAll('select').forEach(function(sel) {
      sel.style.setProperty('color', '#1a1a2e', 'important');
      sel.style.setProperty('-webkit-text-fill-color', '#1a1a2e', 'important');
      sel.style.setProperty('background-color', '#fff', 'important');
    });
    document.querySelectorAll('select option').forEach(function(opt) {
      opt.style.setProperty('color', '#1a1a2e', 'important');
    });
    /* Table headers */
    document.querySelectorAll('.grid-heading-row').forEach(function(row) {
      row.style.setProperty('background', '#eaf2f8', 'important');
      row.querySelectorAll('*').forEach(function(el) {
        el.style.setProperty('color', '#1a1a2e', 'important');
        el.style.setProperty('-webkit-text-fill-color', '#1a1a2e', 'important');
      });
    });
    /* Table body cells */
    document.querySelectorAll('.rows .row, .rows .static-area, .grid-row .static-area').forEach(function(el) {
      el.style.setProperty('color', '#1a1a2e', 'important');
      el.style.setProperty('-webkit-text-fill-color', '#1a1a2e', 'important');
    });
  }

  function findFieldEl(fieldname) {
    return (
      document.querySelector('.frappe-control[data-fieldname="' + fieldname + '"]') ||
      document.querySelector('[data-fieldname="' + fieldname + '"]')
    );
  }

  function createSection(cfg, idx) {
    var section = document.createElement("div");
    section.className = "kya-form-section";
    var header = document.createElement("div");
    header.className = "kya-section-title";
    header.innerHTML = '<span class="kya-section-icon">' + (cfg.icon || "") + '</span> ' + idx + '. ' + cfg.title;
    section.appendChild(header);
    var body = document.createElement("div");
    body.className = "kya-section-body";
    if (cfg.sigGrid) body.classList.add("kya-sig-grid");
    else if (cfg.grid) body.classList.add("kya-grid");
    section.appendChild(body);
    return { section: section, body: body };
  }

  function printForm() { window.print(); }

  function userHasRole(r) {
    return window.frappe && frappe.user_roles && frappe.user_roles.indexOf(r) !== -1;
  }
  function userHasAnyRole(roles) {
    if (!roles || !roles.length) return false;
    for (var i = 0; i < roles.length; i++) { if (userHasRole(roles[i])) return true; }
    return false;
  }
  function isDocOwner() {
    if (!window.frappe || !frappe.web_form_doc) return true;
    var owner = frappe.web_form_doc.doc_owner || frappe.web_form_doc.owner || "";
    return !owner || owner === frappe.session.user;
  }

  function setupSignaturePermissions(route) {
    var sigMap = SIGNATURE_ROLES[route];
    if (!sigMap) return;
    Object.keys(sigMap).forEach(function(fieldname) {
      var el = findFieldEl(fieldname);
      if (!el) return;
      var allowedRoles = sigMap[fieldname];
      var canSign = false;
      if (allowedRoles === null) {
        canSign = isDocOwner();
      } else {
        canSign = userHasAnyRole(allowedRoles);
      }
      if (canSign) {
        el.classList.remove("read-only");
        el.removeAttribute("data-read-only");
        var canvas = el.querySelector("canvas");
        if (canvas) canvas.style.pointerEvents = "auto";
        var clearBtn = el.querySelector(".btn-xs");
        if (clearBtn) clearBtn.style.display = "";
        var input = el.querySelector("input");
        if (input) { input.removeAttribute("readonly"); input.removeAttribute("disabled"); }
      } else {
        el.classList.add("read-only");
        el.setAttribute("data-read-only", "1");
        var canvas2 = el.querySelector("canvas");
        if (canvas2) canvas2.style.pointerEvents = "none";
        var clearBtn2 = el.querySelector(".btn-xs");
        if (clearBtn2) clearBtn2.style.display = "none";
      }
    });
  }

  function setupFieldEditPermissions(route) {
    var isEditor = userHasAnyRole(EDITOR_ROLES);
    var owner = isDocOwner();
    if (isEditor || owner) return;
    var sections = FORM_SECTIONS[route];
    if (!sections) return;
    sections.forEach(function(sec) {
      if (sec.sigGrid) return;
      sec.fields.forEach(function(fn) {
        var el = findFieldEl(fn);
        if (!el) return;
        var inputs = el.querySelectorAll("input, textarea, select");
        inputs.forEach(function(inp) {
          inp.setAttribute("readonly", "readonly");
          inp.setAttribute("disabled", "disabled");
        });
      });
    });
  }

  function setupWorkflowActions(wrapper) {
    if (!window.frappe || !frappe.web_form_doc) return;
    // doc_name = nom du document sauvegardd (null/vide pour nouveau formulaire)
    // Ne PAS utiliser .name qui contient le nom du web form (ex: "demande-achat")
    var docName = frappe.web_form_doc.doc_name;
    if (!docName) return;  // nouveau formulaire — pas d'actions workflow
    var doctype = frappe.web_form_doc.doc_type;
    if (!doctype) return;
    frappe.call({
      method: "kya_hr.api.get_kya_workflow_actions",
      args: { doctype: doctype, docname: docName },
      async: true,
      callback: function (r) {
        if (!r || !r.message) return;
        var data = r.message;
        var actions = data.actions || [];
        if (!actions.length && !data.workflow_state) return;
        var stateEl = document.createElement("div");
        stateEl.className = "kya-wf-state";
        var stateClass = "kya-state-pending";
        var ws = data.workflow_state || "";
        if (/approuv/i.test(ws)) stateClass = "kya-state-approved";
        else if (/rejet/i.test(ws)) stateClass = "kya-state-rejected";
        else if (ws === "Brouillon") stateClass = "kya-state-draft";
        stateEl.innerHTML =
          '<span class="kya-state-label">\u00c9tat :</span> ' +
          '<span class="kya-state-badge ' + stateClass + '">' + ws + '</span>';
        if (actions.length) {
          var btnC = document.createElement("div");
          btnC.className = "kya-wf-actions";
          actions.forEach(function (a) {
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className = /rejeter|refuser/i.test(a.action) ? "kya-btn-reject" : "kya-btn-approve";
            btn.textContent = a.action;
            btn.title = "\u2192 " + a.next_state;
            btn.addEventListener("click", function () {
              applyWorkflowAction(doctype, docName, a.action, a.next_state);
            });
            btnC.appendChild(btn);
          });
          stateEl.appendChild(btnC);
        }
        var tb = wrapper.querySelector(".kya-wf-toolbar");
        if (tb) tb.parentNode.insertBefore(stateEl, tb.nextSibling);
        else {
          var hd = wrapper.querySelector(".kya-wf-header");
          if (hd) hd.parentNode.insertBefore(stateEl, hd.nextSibling);
        }
      }
    });
  }

  function applyWorkflowAction(doctype, docname, action, nextState) {
    if (!confirm("Confirmer l\u2019action : " + action + " ?\n(\u2192 " + nextState + ")")) return;
    frappe.call({
      method: "kya_hr.api.apply_kya_workflow_action",
      args: { doctype: doctype, docname: docname, action: action },
      callback: function (r) {
        if (r && r.message && r.message.status === "success") {
          frappe.msgprint({
            title: "Action effectu\u00e9e",
            message: "Le document est maintenant : <b>" + r.message.workflow_state + "</b>",
            indicator: "green"
          });
          setTimeout(function () { window.location.reload(); }, 1500);
        }
      },
      error: function () {
        frappe.msgprint({
          title: "Erreur",
          message: "Impossible d\u2019effectuer cette action.",
          indicator: "red"
        });
      }
    });
  }

  /* ===== ADMIN PREVIEW BUTTON ======================== */
  function setupAdminPreviewButton() {
    if (!userHasRole("System Manager") && !userHasRole("HR Manager") && !userHasRole("Administrator")) return;
    var allForms = [
      { label: "Permission Sortie Stagiaire", route: "permission-sortie-stagiaire" },
      { label: "Permission Sortie Employé", route: "permission-sortie-employe" },
      { label: "Demande d'Achat", route: "demande-achat" },
      { label: "Demande de Congé", route: "demande-conge" },
      { label: "PV Sortie Matériel", route: "pv-sortie-materiel" },
      { label: "Planning Congé", route: "planning-conge" },
      { label: "Bilan de Stage", route: "bilan-fin-de-stage" }
    ];
    var currentRoute = getRoute();
    var bar = document.createElement("div");
    bar.className = "kya-admin-preview-bar";
    var panel = document.createElement("div");
    panel.className = "kya-preview-panel";
    panel.style.display = "none";
    panel.innerHTML = '<h4>🔗 Liens de prévisualisation</h4>' +
      '<div class="kya-preview-forms">' +
      allForms.map(function(f) {
        var url = window.location.origin + "/" + f.route + "/new";
        var isCurrent = f.route === currentRoute;
        return '<div class="kya-preview-form-link">' +
          '<span' + (isCurrent ? ' style="font-weight:800;"' : '') + '>' + f.label + '</span>' +
          '<a href="' + url + '" target="_blank">Ouvrir →</a>' +
          '</div>';
      }).join("") + '</div>' +
      '<button class="kya-preview-copy" onclick="(function(){var url=window.location.origin+\'/\'+\'' + currentRoute + '\'+\'/new\';navigator.clipboard&&navigator.clipboard.writeText(url).then(function(){this.textContent=\'✓ Copié !\';}.bind(this));}).call(this)">📋 Copier lien du formulaire actuel</button>';
    var toggle = document.createElement("button");
    toggle.className = "kya-preview-toggle";
    toggle.innerHTML = "ðŸ‘ï¸ Aperçu Admin";
    toggle.addEventListener("click", function() {
      var vis = panel.style.display === "none";
      panel.style.display = vis ? "block" : "none";
      toggle.innerHTML = vis ? "✕ Fermer" : "ðŸ‘ï¸ Aperçu Admin";
    });
    bar.appendChild(panel);
    bar.appendChild(toggle);
    document.body.appendChild(bar);
  }

  /* ===== MAIN RESTRUCTURE ============================= */
  function restructureForm() {
    var route = getRoute();
    var sections = FORM_SECTIONS[route];
    var meta = FORM_META[route];
    if (!sections || !meta) return;

    var formBody =
      document.querySelector(".web-form-wrapper") ||
      document.querySelector(".web-form-body") ||
      document.querySelector(".web-form .form-body") ||
      document.querySelector("form.web-form") ||
      document.querySelector(".frappe-form");
    if (!formBody) return;
    if (formBody.querySelector(".kya-form-section")) return;

    /* cleanup old headers */
    document.querySelectorAll(".introduction .kya-wf-header, .web-form-header .kya-wf-header").forEach(function(h){h.remove();});
    document.querySelectorAll(".introduction .kya-wf-info, .web-form-header .kya-wf-info").forEach(function(h){h.remove();});

    var allFields = {};
    sections.forEach(function (sec) {
      sec.fields.forEach(function (fn) {
        var el = findFieldEl(fn);
        if (el) allFields[fn] = el;
      });
    });

    var wrapper = document.createElement("div");
    wrapper.className = "kya-sections-wrapper";

    /* === HEADER: 2-column Ordre de Mission style === */
    var docName = "";
    if (window.frappe && frappe.web_form_doc) {
      docName = frappe.web_form_doc.doc_name || frappe.web_form_doc.name || "";
    }
    var docDisplay = docName || "PROVISOIRE";

    var header = document.createElement("div");
    header.className = "kya-wf-header";
    header.innerHTML =
      '<div class="kya-header-row">' +
        '<div class="kya-header-left">' +
          '<img class="kya-logo" src="/assets/kya_hr/images/logo_kya.png" ' +
          "alt=\"KYA-Energy Group\" onerror=\"this.src='/files/vrai.png'\">" +
        '</div>' +
        '<div class="kya-header-right">' +
          '<h3 class="kya-title">' + meta.title + '</h3>' +
          '<span class="kya-slogan">Move beyond the sky!</span>' +
          '<div class="kya-company-details">' +
            'info@kya-energy.com<br>' +
            'N\u00b0 RCCM : TG-LOM 2015 B 975<br>' +
            'NIF : 1000430317 | CNSS : 48863' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="kya-header-divider"></div>' +
      '<div class="kya-doc-number">' +
        'N\u00b0 <span class="kya-doc-name">' + docDisplay + '</span>' +
        (meta.ref ? ' &mdash; <span class="kya-doc-ref-inline">' + meta.ref + '</span>' : '') +
      '</div>';
    wrapper.appendChild(header);

    /* Toolbar */
    var toolbar = document.createElement("div");
    toolbar.className = "kya-wf-toolbar";
    toolbar.innerHTML =
      '<button type="button" class="kya-btn-print" title="Imprimer">\u{1F5A8}\uFE0F Imprimer</button>' +
      '<button type="button" class="kya-btn-pdf" title="PDF">\u{1F4E5} PDF</button>';
    wrapper.appendChild(toolbar);
    setTimeout(function () {
      var bp = toolbar.querySelector(".kya-btn-print");
      var bd = toolbar.querySelector(".kya-btn-pdf");
      if (bp) bp.addEventListener("click", printForm);
      if (bd) bd.addEventListener("click", printForm);
    }, 0);

    /* Info box */
    var info = document.createElement("div");
    info.className = "kya-wf-info";
    info.innerHTML =
      (meta.subtitle ? '<b>' + meta.subtitle + '</b> &mdash; ' : '') +
      'Circuit d\u2019approbation : <b>' + meta.workflow + '</b>';
    wrapper.appendChild(info);

    /* Build sections */
    var sectionIdx = 0;
    sections.forEach(function (sec) {
      sectionIdx++;
      var s = createSection(sec, sectionIdx);
      sec.fields.forEach(function (fn) {
        var el = allFields[fn];
        if (!el) return;
        if (sec.grid && sec.grid[fn] === "span 2") el.classList.add("kya-grid-span-2");
        else if (sec.grid && sec.grid[fn] === "col") el.classList.add("kya-grid-col");
        s.body.appendChild(el);
      });
      wrapper.appendChild(s.section);
    });

    /* Footer */
    var footer = document.createElement("div");
    footer.className = "kya-wf-footer";
    footer.innerHTML =
      '<strong class="kya-footer-brand">KYA-Energy Group</strong>' +
      ' | LOM\u00c9 - TOGO | T\u00e9l. : +228 70 45 34 81' +
      '<span class="kya-footer-slogan">Move beyond the sky!</span>';
    wrapper.appendChild(footer);

    formBody.insertBefore(wrapper, formBody.firstChild);
    formBody.classList.add("kya-restructured");
    setLoadingState(false);

    setupWorkflowActions(wrapper);
    setTimeout(function() {
      setupSignaturePermissions(route);
      setupFieldEditPermissions(route);
      stabilizeSignaturePads(route);
    }, 500);

    var defaultHead = document.querySelector(".web-form-head");
    if (defaultHead) defaultHead.classList.add("kya-hidden");
    var defaultIntro = document.querySelector(".web-form-introduction");
    if (defaultIntro) defaultIntro.style.display = "none";

    ["employee_name","department","designation","nombre_jours","montant_total","note_globale","mention"].forEach(function(fn){
      var el = findFieldEl(fn);
      if (el) el.setAttribute("data-read-only", "1");
    });
  }

  function setupEmployeeAutoFill() {
    var route = getRoute();
    if (!FORM_SECTIONS[route]) return;
    var empField = findFieldEl("employee");
    if (!empField) return;
    var empInput = empField.querySelector("input");
    if (!empInput) return;
    var canPickAnyEmployee = userHasAnyRole(["HR Manager", "HR User", "System Manager"]);

    function lockEmployeeField() {
      if (canPickAnyEmployee) return;
      var controls = empField.querySelectorAll("input, select, .awesomplete input");
      controls.forEach(function (ctrl) {
        ctrl.setAttribute("readonly", "readonly");
        ctrl.setAttribute("disabled", "disabled");
      });
      empField.setAttribute("data-read-only", "1");
    }

    function fillFromEmployeeRecord(emp) {
      if (!emp || !emp.name) return;
      // Use Frappe Web Form API first (triggers internal reactivity), fallback DOM
      var wf = window.frappe && frappe.web_form;
      function setVal(fn, val) {
        if (val == null || val === "") return;
        if (wf && typeof wf.set_value === "function") {
          try { wf.set_value(fn, val); } catch (e) {}
        }
        var el = findFieldEl(fn);
        if (el) {
          var input = el.querySelector("input, select, textarea");
          if (input) {
            input.value = val;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
          }
        }
      }
      setVal("employee", emp.name);
      setVal("employee_name", emp.employee_name);
      setVal("department", emp.department);
      // retry once after 400ms because Frappe re-renders linked fields asynchronously
      setTimeout(function () {
        setVal("employee_name", emp.employee_name);
        setVal("department", emp.department);
      }, 400);
      lockEmployeeField();
    }

    function fetchAndFillFromSession() {
      if (!window.frappe || frappe.session.user === "Guest") return;
      if (empInput.value && empInput.value.trim()) return; // déjÃ  rempli
      frappe.call({
        method: "kya_hr.api.get_employee_from_user",
        args: {},
        callback: function (r) {
          if (r && r.message) {
            fillFromEmployeeRecord(r.message);
            // Injecter widget recherche par nom si l'employé n'est toujours pas reconnu
            if (!r.message.name) injectNameSearchWidget();
          } else {
            // Aucune fiche employé liée au compte → proposer la recherche par nom
            injectNameSearchWidget();
          }
          lockEmployeeField();
        }
      });
    }

    function injectNameSearchWidget() {
      if (empField.querySelector(".kya-name-search-widget")) return;
      var widget = document.createElement("div");
      widget.className = "kya-name-search-widget";
      widget.style.cssText = "margin-top:8px;padding:10px 12px;background:#fff8e1;border:1px solid #ffe082;border-radius:6px;font-size:13px;";
      widget.innerHTML =
        '<p style="margin:0 0 6px;color:#5d4037;font-weight:600;">Votre compte n\'est pas encore lié Ã  une fiche RH.</p>' +
        '<p style="margin:0 0 8px;color:#5d4037;">Tapez votre nom complet pour confirmer votre identité :</p>' +
        '<div style="display:flex;gap:8px;align-items:center;">' +
          '<input type="text" class="kya-name-search-input" placeholder="Ex: Jean Kofi MENSAH" ' +
            'style="flex:1;padding:6px 10px;border:1px solid #bbb;border-radius:4px;font-size:13px;" />' +
          '<button type="button" class="kya-name-search-btn" ' +
            'style="padding:6px 14px;background:#1a73e8;color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:600;">Rechercher</button>' +
        '</div>' +
        '<p class="kya-name-search-result" style="margin:6px 0 0;color:#c62828;min-height:18px;"></p>';

      empField.appendChild(widget);

      var searchInput = widget.querySelector(".kya-name-search-input");
      var searchBtn = widget.querySelector(".kya-name-search-btn");
      var resultMsg = widget.querySelector(".kya-name-search-result");

      function doSearch() {
        var term = searchInput.value.trim();
        if (term.length < 2) {
          resultMsg.textContent = "Veuillez saisir au moins 2 caractères.";
          resultMsg.style.color = "#c62828";
          return;
        }
        resultMsg.textContent = "Recherche en cours…";
        resultMsg.style.color = "#555";
        frappe.call({
          method: "kya_hr.api.search_employee_by_name",
          args: { search_term: term },
          callback: function (r) {
            if (r && r.message) {
              var emp = r.message;
              resultMsg.textContent = "Correspondance trouvée : " + emp.employee_name + " (" + emp.name + ")";
              resultMsg.style.color = "#2e7d32";
              fillFromEmployeeRecord(emp);
              // Masquer le widget après succès
              setTimeout(function () { widget.style.display = "none"; }, 1500);
            } else {
              resultMsg.textContent = "Aucune correspondance avec votre compte. Contactez les RH.";
              resultMsg.style.color = "#c62828";
            }
          }
        });
      }

      searchBtn.addEventListener("click", doSearch);
      searchInput.addEventListener("keydown", function (e) { if (e.key === "Enter") doSearch(); });
    }

    // Auto-remplissage au chargement (nouveaux formulaires)
    var isNew = !window.location.search.includes("name=") &&
                !window.location.search.includes("docname=") &&
                (window.location.pathname.includes("/new") || !window.frappe || !frappe.web_form_doc || !frappe.web_form_doc.doc_name);
    if (isNew) {
      fetchAndFillFromSession();
    } else {
      lockEmployeeField();
    }

    empInput.addEventListener("change", function () {
      var val = empInput.value;
      if (val && val.length > 3) {
        frappe.call({
          method: "frappe.client.get_value",
          args: { doctype: "Employee", filters: { name: val }, fieldname: ["employee_name", "department"] },
          callback: function (r) {
            if (!r || !r.message) return;
            var nf = findFieldEl("employee_name");
            var df = findFieldEl("department");
            if (nf) { var ni = nf.querySelector("input"); if (ni) { ni.value = r.message.employee_name || ""; ni.dispatchEvent(new Event("change")); } }
            if (df) { var di = df.querySelector("input"); if (di) { di.value = r.message.department || ""; di.dispatchEvent(new Event("change")); } }
            lockEmployeeField();
          }
        });
      }
    });
    lockEmployeeField();
  }

  function forceSignatureFieldSize(el) {
    if (!el) return;
    var field = el.querySelector(".signature-field");
    var pad = el.querySelector(".signature-pad");
    var canvas = el.querySelector("canvas");
    var display = el.querySelector(".signature-display");
    var img = display ? display.querySelector("img") : null;

    var H = 160; // hauteur fixe (px) — était 130, bumped to fix miniaturisation

    if (field) {
      field.style.minHeight = H + "px";
      field.style.height = H + "px";
    }
    if (pad) {
      pad.style.minHeight = H + "px";
      pad.style.height = H + "px";
      pad.style.width = "100%";
    }
    if (canvas) {
      canvas.style.height = H + "px";
      canvas.style.maxHeight = H + "px";
      canvas.style.width = "100%";
      // Corrige l'échelle interne : le bitmap doit correspondre à la taille affichée * DPR
      if (!canvas.dataset.kyaScaled) {
        try {
          var ratio = window.devicePixelRatio || 1;
          var w = canvas.offsetWidth || canvas.clientWidth || 400;
          canvas.width = Math.round(w * ratio);
          canvas.height = Math.round(H * ratio);
          var ctx = canvas.getContext("2d");
          if (ctx) { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.scale(ratio, ratio); }
          canvas.dataset.kyaScaled = "1";
        } catch (e) { /* ignore */ }
      }
    }
    if (display) {
      display.style.minHeight = H + "px";
    }
    if (img) {
      img.style.maxHeight = H + "px";
      img.style.maxWidth = "100%";
      img.style.width = "auto";
      img.style.height = "auto";
      img.style.objectFit = "contain";
    }
  }

  function stabilizeSignaturePads(route) {
    var sections = FORM_SECTIONS[route] || [];
    var sigFields = [];

    sections.forEach(function (sec) {
      (sec.fields || []).forEach(function (fn) {
        if (/^signature_/i.test(fn)) sigFields.push(fn);
      });
    });

    sigFields.forEach(function (fn) {
      var el = findFieldEl(fn);
      if (!el) return;

      forceSignatureFieldSize(el);

      if (el.getAttribute("data-kya-sig-fix-bound") === "1") return;
      el.setAttribute("data-kya-sig-fix-bound", "1");

      var obs = new MutationObserver(function () {
        forceSignatureFieldSize(el);
      });
      obs.observe(el, { childList: true, subtree: true, attributes: true });

      setTimeout(function () { forceSignatureFieldSize(el); }, 500);
      setTimeout(function () { forceSignatureFieldSize(el); }, 1500);
    });
  }

  /* ───────────────────────────────────────────────────────────────
   * LIVE AMOUNT COMPUTE
   * Calcul en temps réel des montants dans les lignes + total
   * Routes: demande-achat, bon-commande, appel-offre, brouillard-caisse, etat-recap
   * ───────────────────────────────────────────────────────────── */
  var LIVE_AMOUNT_CONFIG = {
    "demande-achat": {
      tableField: "items",
      qtyField: "quantite",
      priceField: "prix_unitaire",
      amountField: "montant",
      totalField: "montant_total"
    },
    "bon-commande": {
      tableField: "items",
      qtyField: "quantite",
      priceField: "prix_unitaire",
      amountField: "montant",
      totalField: "montant_total"
    },
    "appel-offre": {
      tableField: "items",
      qtyField: "quantite",
      priceField: "prix_unitaire_estime",
      amountField: "montant_estime",
      totalField: "budget_estime"
    },
    "brouillard-caisse": {
      tableField: "lignes",
      qtyField: null,
      priceField: null,
      amountField: "montant",
      totalField: "total_montant"
    }
  };

  function formatXOF(n) {
    if (n == null || isNaN(n)) return "0 XOF";
    try {
      return Number(n).toLocaleString("fr-FR", { maximumFractionDigits: 0 }) + " XOF";
    } catch (e) {
      return Math.round(n) + " XOF";
    }
  }

  function setupLiveAmountCompute(route) {
    var cfg = LIVE_AMOUNT_CONFIG[route];
    if (!cfg) return;
    var tableWrapper = document.querySelector('[data-fieldname="' + cfg.tableField + '"]');
    if (!tableWrapper) return;

    function recompute() {
      var rows = tableWrapper.querySelectorAll(".grid-row, .rows .grid-row");
      var total = 0;
      rows.forEach(function (row) {
        var qtyInput = cfg.qtyField ? row.querySelector('[data-fieldname="' + cfg.qtyField + '"] input') : null;
        var priceInput = cfg.priceField ? row.querySelector('[data-fieldname="' + cfg.priceField + '"] input') : null;
        var amountInput = row.querySelector('[data-fieldname="' + cfg.amountField + '"] input');
        if (!amountInput) return;
        var amount;
        if (qtyInput && priceInput) {
          var q = parseFloat((qtyInput.value || "0").replace(/\s/g, "").replace(",", ".")) || 0;
          var p = parseFloat((priceInput.value || "0").replace(/\s/g, "").replace(",", ".")) || 0;
          amount = q * p;
          // show computed value (amountInput is read_only but we can set its value for display)
          amountInput.value = amount ? amount.toLocaleString("fr-FR") : "";
          amountInput.dispatchEvent(new Event("change", { bubbles: true }));
        } else {
          amount = parseFloat((amountInput.value || "0").replace(/\s/g, "").replace(",", ".")) || 0;
        }
        total += amount || 0;
      });
      if (cfg.totalField) {
        var totalEl = document.querySelector('[data-fieldname="' + cfg.totalField + '"] input');
        if (totalEl) {
          totalEl.value = total ? total.toLocaleString("fr-FR") : "";
          totalEl.dispatchEvent(new Event("change", { bubbles: true }));
        }
        // Injecter/mettre à jour badge visible au-dessus des sections
        var badgeId = "kya-total-badge-" + route;
        var badge = document.getElementById(badgeId);
        if (!badge) {
          badge = document.createElement("div");
          badge.id = badgeId;
          badge.className = "kya-total-badge";
          badge.style.cssText = "margin:12px 0;padding:14px 20px;background:linear-gradient(135deg,#f7941d,#ea580c);" +
            "color:#fff;font-size:20px;font-weight:700;border-radius:8px;text-align:center;" +
            "box-shadow:0 4px 12px rgba(247,148,29,0.3);letter-spacing:0.5px;";
          tableWrapper.parentNode.insertBefore(badge, tableWrapper.nextSibling);
        }
        badge.innerHTML = '💰 MONTANT TOTAL : <span style="font-size:24px;">' + formatXOF(total) + '</span>';
      }
    }

    // Débounce
    var t = null;
    function scheduleRecompute() {
      clearTimeout(t);
      t = setTimeout(recompute, 150);
    }

    // Écouter tous les inputs dans la table (délégation)
    tableWrapper.addEventListener("input", scheduleRecompute, true);
    tableWrapper.addEventListener("change", scheduleRecompute, true);
    tableWrapper.addEventListener("click", scheduleRecompute, true); // pour add/remove row

    // Observer les changements DOM (nouvelles lignes)
    var mo = new MutationObserver(scheduleRecompute);
    mo.observe(tableWrapper, { childList: true, subtree: true });

    // Recompute initial après 500ms
    setTimeout(recompute, 500);
    setTimeout(recompute, 1500);
  }

  /* ===================================================================
   * POPUP INLINE — Nouveau Fournisseur (Supplier) / Nouveau Client (Customer)
   * Routes : appel-offre (Supplier) / bon-commande (Customer)
   * Si la responsable Achats ne trouve pas le tiers, elle peut :
   *   1) Créer le tiers dans la base (Supplier/Customer) en 1 clic
   *   2) Continuer sans l'enregistrer (fournisseur_nom seul)
   * ================================================================= */
  var PARTY_CONFIG = {
    "bon-commande": {
      linkField: "fournisseur",      // Link
      nameField: "fournisseur_nom",
      phoneField: "fournisseur_telephone",
      emailField: "fournisseur_email",
      addressField: "fournisseur_adresse",
      cityField: "fournisseur_ville",
      doctype: "Customer",
      dtLabel: "Client",
      dtLabelLower: "client"
    },
    "appel-offre": {
      linkField: "fournisseur",
      nameField: "fournisseur_nom",
      phoneField: "fournisseur_telephone",
      emailField: "fournisseur_email",
      addressField: "fournisseur_adresse",
      cityField: "fournisseur_ville",
      doctype: "Supplier",
      dtLabel: "Fournisseur",
      dtLabelLower: "fournisseur"
    }
  };

  function getFieldInputValue(fieldname) {
    var el = findFieldEl(fieldname);
    if (!el) return "";
    var inp = el.querySelector("input, textarea, select");
    return inp ? (inp.value || "") : "";
  }
  function setFieldInputValue(fieldname, value) {
    if (window.frappe && frappe.web_form && frappe.web_form.set_value) {
      try { frappe.web_form.set_value(fieldname, value); } catch (e) { /* fallback */ }
    }
    var el = findFieldEl(fieldname);
    if (!el) return;
    var inp = el.querySelector("input, textarea, select");
    if (inp) { inp.value = value || ""; inp.dispatchEvent(new Event("input", { bubbles: true })); inp.dispatchEvent(new Event("change", { bubbles: true })); }
  }

  function openPartyPopup(cfg) {
    if (document.getElementById("kya-party-modal")) return;
    var overlay = document.createElement("div");
    overlay.id = "kya-party-modal";
    overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:99999;display:flex;align-items:center;justify-content:center;padding:16px;";
    overlay.innerHTML = ''
      + '<div style="background:#fff;border-radius:12px;max-width:560px;width:100%;max-height:90vh;overflow:auto;padding:24px;box-shadow:0 10px 40px rgba(0,0,0,0.3);">'
      + '  <h3 style="margin:0 0 8px;color:#1a1a2e;">Nouveau ' + cfg.dtLabel + '</h3>'
      + '  <p style="color:#555;margin:0 0 16px;font-size:14px;">Ce ' + cfg.dtLabelLower + ' n\u2019est pas dans la base. Vous pouvez l\u2019enregistrer ici ou continuer sans l\u2019enregistrer.</p>'
      + '  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
      + '    <label style="grid-column:span 2;font-size:12px;color:#1a1a2e;font-weight:600;">Nom / Raison sociale *<input id="kya-pp-name" type="text" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;margin-top:4px;color:#1a1a2e;" /></label>'
      + '    <label style="font-size:12px;color:#1a1a2e;font-weight:600;">T\u00e9l\u00e9phone<input id="kya-pp-phone" type="text" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;margin-top:4px;color:#1a1a2e;" /></label>'
      + '    <label style="font-size:12px;color:#1a1a2e;font-weight:600;">Email<input id="kya-pp-email" type="email" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;margin-top:4px;color:#1a1a2e;" /></label>'
      + '    <label style="grid-column:span 2;font-size:12px;color:#1a1a2e;font-weight:600;">Adresse<input id="kya-pp-address" type="text" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;margin-top:4px;color:#1a1a2e;" /></label>'
      + '    <label style="font-size:12px;color:#1a1a2e;font-weight:600;">Ville<input id="kya-pp-city" type="text" value="Lom\u00e9" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;margin-top:4px;color:#1a1a2e;" /></label>'
      + '  </div>'
      + '  <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px;flex-wrap:wrap;">'
      + '    <button type="button" id="kya-pp-cancel" style="padding:8px 16px;background:#e0e0e0;color:#333;border:none;border-radius:6px;cursor:pointer;">Annuler</button>'
      + '    <button type="button" id="kya-pp-skip" style="padding:8px 16px;background:#f57c00;color:#fff;border:none;border-radius:6px;cursor:pointer;">Continuer sans enregistrer</button>'
      + '    <button type="button" id="kya-pp-save" style="padding:8px 16px;background:#2e7d32;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;">Enregistrer et utiliser</button>'
      + '  </div>'
      + '  <div id="kya-pp-err" style="color:#c62828;margin-top:12px;font-size:13px;display:none;"></div>'
      + '</div>';
    document.body.appendChild(overlay);

    var nameEl = overlay.querySelector("#kya-pp-name");
    if (nameEl) nameEl.value = getFieldInputValue(cfg.nameField) || "";

    function close() { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); }
    overlay.querySelector("#kya-pp-cancel").onclick = close;

    overlay.querySelector("#kya-pp-skip").onclick = function () {
      var name = (overlay.querySelector("#kya-pp-name").value || "").trim();
      if (name) setFieldInputValue(cfg.nameField, name);
      close();
    };

    overlay.querySelector("#kya-pp-save").onclick = function () {
      var errEl = overlay.querySelector("#kya-pp-err");
      var name = (overlay.querySelector("#kya-pp-name").value || "").trim();
      if (!name) { errEl.style.display = "block"; errEl.textContent = "Le nom est obligatoire."; return; }
      var phone = (overlay.querySelector("#kya-pp-phone").value || "").trim();
      var email = (overlay.querySelector("#kya-pp-email").value || "").trim();
      var address = (overlay.querySelector("#kya-pp-address").value || "").trim();
      var city = (overlay.querySelector("#kya-pp-city").value || "").trim();
      errEl.style.display = "none";

      var doc = { doctype: cfg.doctype };
      if (cfg.doctype === "Customer") {
        doc.customer_name = name;
        doc.customer_type = "Company";
        doc.customer_group = "All Customer Groups";
        doc.territory = "All Territories";
      } else {
        doc.supplier_name = name;
        doc.supplier_group = "All Supplier Groups";
      }
      if (phone) doc.mobile_no = phone;
      if (email) doc.email_id = email;

      frappe.call({
        method: "frappe.client.insert",
        args: { doc: doc },
        callback: function (r) {
          if (!r || !r.message) {
            errEl.style.display = "block"; errEl.textContent = "\u00c9chec de l\u2019enregistrement.";
            return;
          }
          var created = r.message.name || name;
          setFieldInputValue(cfg.linkField, created);
          setFieldInputValue(cfg.nameField, name);
          if (phone) setFieldInputValue(cfg.phoneField, phone);
          if (email) setFieldInputValue(cfg.emailField, email);
          if (address) setFieldInputValue(cfg.addressField, address);
          if (city) setFieldInputValue(cfg.cityField, city);
          frappe.show_alert && frappe.show_alert({ message: cfg.dtLabel + " enregistr\u00e9 : " + created, indicator: "green" });
          close();
        },
        error: function (err) {
          errEl.style.display = "block";
          errEl.textContent = "Erreur : " + ((err && err.message) || "impossible de cr\u00e9er le " + cfg.dtLabelLower + ".");
        }
      });
    };
  }

  function setupPartyCreateButton(route) {
    var cfg = PARTY_CONFIG[route];
    if (!cfg) return;
    var linkEl = findFieldEl(cfg.linkField);
    if (!linkEl) return;
    if (linkEl.querySelector(".kya-party-add-btn")) return;

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "kya-party-add-btn";
    btn.textContent = "+ Nouveau " + cfg.dtLabel;
    btn.style.cssText = "margin:6px 0 0;padding:6px 12px;background:#1565c0;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;";
    btn.onclick = function () { openPartyPopup(cfg); };
    linkEl.appendChild(btn);
  }

  function waitForForm() {
    var route = getRoute();
    injectVisibilityPatchCss();
    if (!FORM_SECTIONS[route] && !FORM_META[route]) return;
    setLoadingState(true);
    var formReady = document.querySelector(".frappe-control") || document.querySelector("[data-fieldname]");
    if (formReady) {
      restructureForm();
      setupEmployeeAutoFill();
      stabilizeSignaturePads(route);
      setupLiveAmountCompute(route);
      setupPartyCreateButton(route);
      setTimeout(forceInlineTextVisibility, 200);
      setLoadingState(false);
      return;
    }
    var obs = new MutationObserver(function (m, observer) {
      if (document.querySelector(".frappe-control") || document.querySelector("[data-fieldname]")) {
        observer.disconnect();
        setTimeout(function () {
          restructureForm();
          setupEmployeeAutoFill();
          stabilizeSignaturePads(route);
          setupLiveAmountCompute(route);
          setupPartyCreateButton(route);
          forceInlineTextVisibility();
          setLoadingState(false);
        }, 300);
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
    setTimeout(function () {
      if (!document.querySelector(".kya-form-section")) {
        restructureForm();
        setupEmployeeAutoFill();
      }
      stabilizeSignaturePads(route);
      forceInlineTextVisibility();
      setLoadingState(false);
    }, 2000);
    setTimeout(function () {
      obs.disconnect();
      if (!document.querySelector(".kya-form-section")) {
        restructureForm();
        setupEmployeeAutoFill();
      }
      stabilizeSignaturePads(route);
      forceInlineTextVisibility();
      setLoadingState(false);
    }, 5000);
  }

  window.kyaRestructureForm = function () { restructureForm(); setupEmployeeAutoFill(); };

  // Universal fallback: if a Web Form defines/overrides after_load,
  // ensure KYA branded layout is still applied once fields are mounted.
  if (window.frappe && frappe.web_form && !window.__kyaWfAfterLoadPatched) {
    window.__kyaWfAfterLoadPatched = true;
    var previousAfterLoad = frappe.web_form.after_load;
    frappe.web_form.after_load = function () {
      if (typeof previousAfterLoad === "function") {
        previousAfterLoad.apply(this, arguments);
      }
      setTimeout(function () {
        if (window.kyaRestructureForm) window.kyaRestructureForm();
      }, 120);
    };
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", function() { waitForForm(); setupAdminPreviewButton(); }); }
  else { waitForForm(); setupAdminPreviewButton(); }
  if (window.frappe && window.frappe.ready) { frappe.ready(function () { setTimeout(function() { waitForForm(); setupAdminPreviewButton(); }, 300); }); }
  if (window.frappe && window.frappe.router) { document.addEventListener("page-change", function () { setTimeout(waitForForm, 500); }); }
})();
