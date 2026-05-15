/* ===================================================================
   KYA-Energy Group — Web Form Layout v4
   Design : Ordre de Mission / Fiche officielle KYA
   En-tête 2-colonnes : Logo gauche | Titre + infos droite
   N° de document affiché, sections numérotées,
   permissions par rôle, signatures verrouillées.
   =================================================================== */

/* === Auto-redirect bare web form URLs to /new ==================== */
(function () {
  var KYA_WF_ROUTES = [
    "permission-sortie-stagiaire", "permission-sortie-employe",
    "demande-achat", "pv-sortie-materiel",
    "planning-conge", "bilan-fin-de-stage",
    "appel-offre", "bon-commande", "demande-conge",
    "pv-entree-materiel", "etat-recap", "brouillard-caisse",
    "retour-materiel"
  ];
  var path = window.location.pathname.replace(/^\//, "").replace(/\/$/, "");
  if (KYA_WF_ROUTES.indexOf(path) !== -1) {
    // Bare route without /new — redirect silently
    window.location.replace("/" + path + "/new");
    return; // stop further execution until redirect completes
  }
})();

/* === Redirect Desk /app/<slug>/new -> KYA web form (sauf System Manager) ===
   Empêche les boutons "+ Add" des listes Desk d'ouvrir le form Desk pour
   les DocTypes ayant un web form custom. Les System Managers gardent
   l'accès Desk pour debug/admin. */
(function () {
  var DOCTYPE_TO_WEBFORM = {
    "permission-sortie-stagiaire": "/permission-sortie-stagiaire/new",
    "permission-sortie-employe":  "/permission-sortie-employe/new",
    "demande-achat-kya":          "/demande-achat/new",
    "pv-sortie-materiel":         "/pv-sortie-materiel/new",
    "pv-entree-materiel":         "/pv-entree-materiel/new",
    "planning-conge":             "/planning-conge/new",
    "leave-application":          "/demande-conge/new",
    "bilan-fin-de-stage":         "/bilan-fin-de-stage/new",
    "appel-offre-kya":            "/appel-offre/new",
    "bon-commande-kya":           "/bon-commande/new",
    "etat-recap-cheques":         "/etat-recap/new",
    "brouillard-caisse":          "/brouillard-caisse/new",
    "retour-materiel-kya":        "/retour-materiel/new"
  };

  function targetForCurrentRoute() {
    var path = window.location.pathname;
    // Frappe SPA hash route fallback (#... -> /app/...)
    if (window.location.hash && window.location.hash.charAt(0) === "#") {
      var hp = window.location.hash.replace(/^#/, "");
      if (hp.charAt(0) === "/") path = hp;
    }
    var m = path.match(/^\/app\/([^\/\?]+)\/new(\?.*)?$/);
    if (!m) return null;
    return DOCTYPE_TO_WEBFORM[m[1].toLowerCase()] || null;
  }

  function isSystemManager() {
    var roles = (window.frappe && frappe.boot && frappe.boot.user && frappe.boot.user.roles) ? frappe.boot.user.roles : [];
    return roles.indexOf("System Manager") !== -1;
  }

  function tryRedirect() {
    var target = targetForCurrentRoute();
    if (!target) return;
    if (isSystemManager()) return; // exemption admin
    console.log("[KYA] Desk /new -> web form redirect: " + target);
    window.location.replace(target);
  }

  // Attend frappe.boot.user (jusqu'à ~5s), puis redirige + hooke router.
  var attempts = 0;
  var iv = setInterval(function () {
    attempts++;
    if (window.frappe && frappe.boot && frappe.boot.user) {
      clearInterval(iv);
      tryRedirect();
      if (frappe.router && frappe.router.on) {
        frappe.router.on("change", tryRedirect);
      }
    } else if (attempts >= 50) {
      clearInterval(iv);
    }
  }, 100);
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
        fields: ["annee", "leave_type_par_defaut", "periodes"],
        grid: { annee: "col", leave_type_par_defaut: "col" }
      },
      {
        title: "COMMENTAIRE",
        icon: "\u{1F4AC}",
        fields: ["commentaire_employe"]
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
      }
    ],
    "appel-offre": [
      {
        title: "IDENTIFICATION DU DEMANDEUR",
        icon: "\u{1F464}",
        fields: ["demandeur", "demandeur_name", "service"],
        grid: { demandeur: "col", demandeur_name: "col", service: "span 2" }
      },
      {
        title: "D\u00c9TAILS DE L\u2019APPEL D\u2019OFFRE",
        icon: "\u{1F4CB}",
        fields: ["date_ao", "date_limite", "objet", "demande_achat"],
        grid: { date_ao: "col", date_limite: "col", objet: "span 2", demande_achat: "span 2" }
      },
      {
        title: "ARTICLES \u00c0 CONSULTER",
        icon: "\u{1F6D2}",
        fields: ["items"]
      },
      {
        title: "FOURNISSEURS CONSULT\u00c9S",
        icon: "\u{1F3E2}",
        fields: ["fournisseurs"]
      },
      {
        title: "MODALIT\u00c9S & CRIT\u00c8RES",
        icon: "\u{1F4DD}",
        fields: ["modalites", "criteres_selection", "message_fournisseur"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_demandeur", "signature_daaf", "signature_dg"],
        sigGrid: true
      }
    ],
    "bon-commande": [
      {
        title: "IDENTIFICATION DU FOURNISSEUR",
        icon: "\u{1F3E2}",
        fields: ["fournisseur", "fournisseur_name", "date_bc"],
        grid: { fournisseur: "col", fournisseur_name: "col", date_bc: "span 2" }
      },
      {
        title: "D\u00c9TAILS DE LA COMMANDE",
        icon: "\u{1F4CB}",
        fields: ["objet", "appel_offre", "demande_achat"]
      },
      {
        title: "ARTICLES COMMAND\u00c9S",
        icon: "\u{1F6D2}",
        fields: ["items", "montant_total"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_resp_achats", "signature_daaf", "signature_dg"],
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
        fields: ["leave_type", "from_date", "to_date", "total_leave_days", "posting_date", "description"],
        grid: {
          leave_type: "span 2",
          from_date: "col", to_date: "col",
          total_leave_days: "col", posting_date: "col",
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
    "pv-entree-materiel": [
      {
        title: "INFORMATIONS DE LA R\u00c9CEPTION",
        icon: "\u{1F4E5}",
        fields: ["date_entree", "fournisseur", "fournisseur_libre", "project", "customer", "customer_libre"],
        grid: {
          date_entree: "col", fournisseur: "col",
          fournisseur_libre: "span 2",
          project: "col", customer: "col",
          customer_libre: "span 2"
        }
      },
      {
        title: "ARTICLES RE\u00c7US",
        icon: "\u{1F4E6}",
        fields: ["items"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_achats_stock", "signature_comptable", "signature_audit"],
        sigGrid: true
      }
    ],
    "retour-materiel": [
      {
        title: "INFORMATIONS DU RETOUR",
        icon: "\u{1F4E6}",
        fields: ["pv_sortie_origine", "date_retour", "objet", "project", "customer", "customer_libre"],
        grid: {
          pv_sortie_origine: "span 2",
          date_retour: "col", objet: "span 2",
          project: "col", customer: "col",
          customer_libre: "span 2"
        }
      },
      {
        title: "MAT\u00c9RIELS RETOURN\u00c9S",
        icon: "\u{1F4CB}",
        fields: ["items"]
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_retourneur", "signature_magasin"],
        sigGrid: true
      }
    ],
    "etat-recap": [
      {
        title: "INFORMATIONS G\u00c9N\u00c9RALES",
        icon: "\u{1F4DD}",
        fields: ["date_etat", "redacteur", "redacteur_name", "semaine_du", "semaine_au"],
        grid: {
          date_etat: "col",
          redacteur: "col",
          redacteur_name: "span 2",
          semaine_du: "col",
          semaine_au: "col"
        }
      },
      {
        title: "LISTE DES CH\u00c8QUES",
        icon: "\u{1F4B5}",
        fields: ["lignes", "total_montant", "nombre_cheques", "commentaires"],
        grid: { total_montant: "col", nombre_cheques: "col", commentaires: "span 2" }
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_redacteur", "signature_dfc", "signature_dg", "signature_dga"],
        sigGrid: true
      }
    ],
    "brouillard-caisse": [
      {
        title: "INFORMATIONS DE LA CAISSE",
        icon: "\u{1F4B0}",
        fields: ["date_brouillard", "caissiere", "solde_precedent"],
        grid: { date_brouillard: "col", caissiere: "col", solde_precedent: "span 2" }
      },
      {
        title: "MOUVEMENTS",
        icon: "\u{1F4CA}",
        fields: ["lignes", "total_entrees", "total_sorties", "solde_final"],
        grid: { total_entrees: "col", total_sorties: "col", solde_final: "span 2" }
      },
      {
        title: "VALIDATIONS & SIGNATURES",
        icon: "\u270D\uFE0F",
        fields: ["signature_caissiere", "signature_comptable", "signature_dfc"],
        sigGrid: true
      }
    ]
  };

  var FORM_META = {
    "permission-sortie-stagiaire": {
      title: "DEMANDE DE PERMISSION DE SORTIE",
      subtitle: "Stagiaire",
      workflow: "Ma\u00eetre de Stage \u2192 Resp. Stagiaires \u2192 Direction"
    },
    "permission-sortie-employe": {
      title: "DEMANDE DE PERMISSION DE SORTIE",
      subtitle: "Employ\u00e9",
      workflow: "Chef de Service \u2192 RH \u2192 Direction"
    },
    "demande-achat": {
      title: "FICHE D\u2019ENGAGEMENT DE D\u00c9PENSES",
      subtitle: "Approvisionnement",
      workflow: "Chef \u2192 Auditeur \u2192 Responsable Comptable \u2192 Directeur G\u00e9n\u00e9ral"
    },
    "pv-sortie-materiel": {
      title: "PV DE SORTIE DE MAT\u00c9RIEL",
      subtitle: "Achat et Stock",
      workflow: "Chef \u2192 Audit \u2192 Direction \u2192 Magasin"
    },
    "planning-conge": {
      title: "PLANNING DE CONG\u00c9 ANNUEL",
      subtitle: "Ressources Humaines",
      workflow: "Employ\u00e9 \u2192 RH \u2192 DG"
    },
    "demande-conge": {
      title: "DEMANDE DE CONG\u00c9",
      subtitle: "Ressources Humaines",
      workflow: "Employ\u00e9 \u2192 Sup\u00e9rieur \u2192 RH \u2192 DG"
    },
    "bilan-fin-de-stage": {
      title: "BILAN DE FIN DE STAGE",
      subtitle: "Formation & Stages",
      workflow: "Stagiaire \u2192 Encadrant \u2192 RH"
    },
    "appel-offre": {
      title: "APPEL D\u2019OFFRE FOURNISSEURS",
      subtitle: "Achats & Approvisionnement",
      workflow: "Demandeur \u2192 Resp. Achats \u2192 Responsable Comptable \u2192 Directeur G\u00e9n\u00e9ral"
    },
    "bon-commande": {
      title: "BON DE COMMANDE",
      subtitle: "Achats & Approvisionnement",
      workflow: "Resp. Achats \u2192 Responsable Comptable \u2192 Directeur G\u00e9n\u00e9ral"
    },
    "demande-achat-old": {
      title: "DEMANDE D\u2019ACHAT",
      subtitle: "Approvisionnement",
      workflow: "Demandeur \u2192 Chef \u2192 Responsable Comptable \u2192 Directeur G\u00e9n\u00e9ral"
    },
    "etat-recap": {
      title: "\u00c9TAT R\u00c9CAPITULATIF DES CH\u00c8QUES",
      subtitle: "Comptabilit\u00e9 & Tr\u00e9sorerie",
      workflow: "R\u00e9dacteur \u2192 Validation DFC \u2192 Valid\u00e9 DFC"
    },
    "brouillard-caisse": {
      title: "BROUILLARD DE CAISSE",
      subtitle: "Comptabilit\u00e9 & Tr\u00e9sorerie",
      workflow: "Caissier \u2192 Comptable \u2192 Responsable Comptable"
    },
    "pv-entree-materiel": {
      title: "PV DE R\u00c9CEPTION DE MAT\u00c9RIELS",
      subtitle: "Achats & Stock \u2014 AEA-ENG-32-V01",
      workflow: "Achats & Stock \u2192 Comptabilit\u00e9 \u2192 Audit Interne"
    },
    "retour-materiel": {
      title: "RETOUR DE MAT\u00c9RIEL AU MAGASIN",
      subtitle: "Achats et Stock",
      workflow: "Retourneur \u2192 Responsable Magasin"
    }
  };

  /* Signature -> role mapping */
  var SIGNATURE_ROLES = {
    "permission-sortie-stagiaire": {
      signature_stagiaire: null,
      signature_chef: ["Chef Service", "HR Manager", "System Manager"],
      signature_resp_stagiaires: ["Responsable des Stagiaires", "HR Manager", "HR User", "System Manager"],
      signature_dg: ["Directeur Général", "System Manager"]
    },
    "permission-sortie-employe": {
      signature_employe: null,
      signature_chef: ["Chef Service", "HR Manager", "System Manager"],
      signature_rh: ["HR Manager", "HR User", "System Manager"],
      signature_dga: ["DGA", "Directeur Général", "System Manager"]
    },
    "demande-achat": {
      signature_demandeur: null,
      signature_chef: ["Chef Service", "System Manager"],
      signature_dga: ["DGA", "Responsable Comptable", "System Manager"],
      signature_dg: ["Directeur Général", "System Manager"]
    },
    "pv-sortie-materiel": {
      signature_demandeur: null,
      signature_chef: ["Chef Service", "System Manager"],
      signature_audit: ["Auditeur Interne", "DGA", "System Manager"],
      signature_dga: ["DGA", "Directeur Général", "System Manager"],
      signature_magasin: ["Stock Manager", "Stock User", "System Manager"]
    },
    "demande-conge": {
      signature_employe_la: null,
      signature_superieur_la: ["Chef Service", "HR Manager", "System Manager"],
      signature_rh_la: ["HR Manager", "HR User", "Responsable RH", "System Manager"],
      signature_dg_la: ["Directeur Général", "System Manager"]
    },
    "pv-entree-materiel": {
      signature_achats_stock: ["Stock Manager", "Stock User", "Chargé des Stocks", "Responsable Achats", "Purchase Manager", "System Manager"],
      signature_comptable: ["Responsable Comptable", "Accounts Manager", "Accounts User", "System Manager"],
      signature_audit: ["Auditeur Interne", "System Manager"]
    },
    "retour-materiel": {
      signature_retourneur: null,
      signature_magasin: ["Stock Manager", "Stock User", "Chargé des Stocks", "System Manager"]
    },
    "etat-recap": {
      signature_redacteur: null,
      signature_dfc: ["Responsable Comptable", "Accounts Manager", "System Manager"],
      signature_dg: ["Directeur Général", "DG", "System Manager"],
      signature_dga: ["DGA", "Directeur Général", "DG", "System Manager"]
    },
    "brouillard-caisse": {
      signature_caissiere: null,
      signature_comptable: ["Accounts User", "Accounts Manager", "System Manager"],
      signature_dfc: ["Responsable Comptable", "System Manager"]
    }
  };

  var SIGNATURE_STATES = {
    "permission-sortie-stagiaire": {
      signature_stagiaire: ["Brouillon", "En attente Chef"],
      signature_chef: ["En attente Chef"],
      signature_resp_stagiaires: ["En attente Resp. Stagiaires"],
      signature_dg: ["En attente DG"]
    },
    "permission-sortie-employe": {
      signature_employe: ["Brouillon", "En attente Chef"],
      signature_chef: ["En attente Chef"],
      signature_rh: ["En attente RH"],
      signature_dga: ["En attente DGA", "En attente DG"]
    },
    "demande-achat": {
      signature_demandeur: ["Brouillon", "En attente Chef", "En attente Chef Service"],
      signature_chef: ["En attente Chef", "En attente Chef Service"],
      signature_dga: ["En attente DGA", "En attente DAAF"],
      signature_dg: ["En attente DG"]
    },
    "pv-sortie-materiel": {
      signature_demandeur: ["Brouillon", "En attente Chef"],
      signature_chef: ["En attente Chef"],
      signature_audit: ["En attente Audit"],
      signature_dga: ["En attente DGA", "En attente DG"],
      signature_magasin: ["En attente Magasin"]
    },
    "demande-conge": {
      signature_employe_la: ["Brouillon", "Open", "En attente Chef", "En attente Supérieur"],
      signature_superieur_la: ["En attente Chef", "En attente Supérieur"],
      signature_rh_la: ["En attente RH"],
      signature_dg_la: ["En attente DG"]
    },
    "pv-entree-materiel": {
      signature_achats_stock: ["En attente Achats & Stock"],
      signature_comptable: ["En attente Comptable"],
      signature_audit: ["En attente Audit"]
    },
    "retour-materiel": {
      signature_retourneur: ["Brouillon", "En attente Magasin"],
      signature_magasin: ["En attente Magasin"]
    },
    "etat-recap": {
      signature_redacteur: ["Brouillon", "En attente Validation DFC"],
      signature_dfc: ["En attente Validation DFC"],
      signature_dg: ["En attente DG"],
      signature_dga: ["En attente DGA"]
    },
    "brouillard-caisse": {
      signature_caissiere: ["Brouillon", "En attente Comptable"],
      signature_comptable: ["En attente Comptable"],
      signature_dfc: ["En attente DFC"]
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

  function canSelectAnyEmployee() {
    return userHasAnyRole(["System Manager", "HR Manager", "HR User", "Responsable RH"]);
  }
  function isDocOwner() {
    if (!window.frappe || !frappe.web_form_doc) return true;
    var owner = frappe.web_form_doc.doc_owner || frappe.web_form_doc.owner || "";
    return !owner || owner === frappe.session.user;
  }

  function getWorkflowState() {
    if (!window.frappe || !frappe.web_form_doc) return "Brouillon";
    return frappe.web_form_doc.workflow_state || frappe.web_form_doc.statut || frappe.web_form_doc.status || "Brouillon";
  }

  function stateAllowsSignature(route, fieldname) {
    var routeStates = SIGNATURE_STATES[route] || {};
    var allowedStates = routeStates[fieldname];
    if (!allowedStates || !allowedStates.length) return true;
    var state = getWorkflowState();
    return allowedStates.indexOf(state) !== -1;
  }

  function normalizeSignaturePads() {
    document.querySelectorAll('.frappe-control[data-fieldtype="Signature"]').forEach(function (el) {
      var canvas = el.querySelector("canvas");
      if (canvas && !canvas.getAttribute("data-kya-sized")) {
        var width = Math.max(280, Math.round((el.clientWidth || canvas.clientWidth || 320) - 18));
        var height = 150;
        canvas.style.width = "100%";
        canvas.style.height = height + "px";
        if (!canvas.toDataURL || canvas.toDataURL().length < 2000) {
          canvas.width = width;
          canvas.height = height;
        }
        canvas.setAttribute("data-kya-sized", "1");
      }
      var img = el.querySelector(".signature-display img");
      if (img) {
        img.style.width = "100%";
        img.style.maxWidth = "100%";
        img.style.maxHeight = "150px";
        img.style.objectFit = "contain";
      }
    });
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
        canSign = isDocOwner() && stateAllowsSignature(route, fieldname);
      } else {
        canSign = userHasAnyRole(allowedRoles) && stateAllowsSignature(route, fieldname);
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
    var docName = frappe.web_form_doc.doc_name || frappe.web_form_doc.name;
    if (!docName) return;
    var doctype = frappe.web_form_doc.doc_type;
    if (!doctype) return;
    // Skip when on a new/unsaved document — docName is "new" or matches the
    // route slug. Calling the API would surface a misleading "Not Found" popup.
    var route = getRoute();
    var lc = String(docName).toLowerCase();
    if (lc === "new" || lc === "none" || lc === "null" || lc === "undefined" ||
        lc === route || lc.indexOf("/") !== -1) {
      return;
    }
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
    toggle.innerHTML = "👁️ Aperçu Admin";
    toggle.addEventListener("click", function() {
      var vis = panel.style.display === "none";
      panel.style.display = vis ? "block" : "none";
      toggle.innerHTML = vis ? "✕ Fermer" : "👁️ Aperçu Admin";
    });
    bar.appendChild(panel);
    bar.appendChild(toggle);
    document.body.appendChild(bar);
  }

  /* === FORMS qui basculent en mode DÉCORATIF SIMPLE =====
   * Les forms ayant des Tables (DataTable Frappe v16) re-render leur DOM
   * APRÈS notre construction du wrapper, ce qui orpheline notre wrapper en
   * haut (avec sections vides) et affiche le form Desk natif en dessous.
   *
   * Pour ces forms, on bascule en mode "décoratif simple" :
   *  - Header KYA (logo, titre officiel, RCCM, etc.) en haut
   *  - Bandeau circuit d'approbation
   *  - PAS de sections-containers (donc rien à remplir, rien à casser)
   *  - Les champs Frappe restent à leur place naturelle
   *  - Footer KYA en bas
   *
   * Les utilisateurs voient le design KYA + le formulaire fonctionnel.
   */
  // IMPORTANT : ne PAS toucher aux forms qui marchent déjà.
  // Seuls les forms confirmés en bug entrent ici.
  var DECORATIVE_ONLY_FORMS = {
    "etat-recap": 1,
    "brouillard-caisse": 1
  };

  function buildDecorativeShell(route, meta, formBody) {
    // Si déjà construit, no-op
    if (formBody.querySelector(".kya-deco-header")) return;

    /* HEADER décoratif (logo + titre officiel KYA) */
    var docName = "";
    if (window.frappe && frappe.web_form_doc) {
      docName = frappe.web_form_doc.doc_name || frappe.web_form_doc.name || "";
    }
    if (docName && (docName === route || docName.toLowerCase() === route.toLowerCase())) {
      docName = "";
    }
    var docDisplay = docName || "PROVISOIRE";

    var header = document.createElement("div");
    header.className = "kya-deco-header kya-wf-header";
    header.innerHTML =
      '<div class="kya-header-row">' +
        '<div class="kya-header-left">' +
          '<img class="kya-logo" src="/assets/kya_hr/images/logo_kya.png" ' +
          'alt="KYA-Energy Group" onerror="this.src=\'/files/vrai.png\'">' +
        '</div>' +
        '<div class="kya-header-right">' +
          '<h3 class="kya-title">' + meta.title + '</h3>' +
          '<span class="kya-slogan">Move beyond the sky!</span>' +
          '<div class="kya-company-details">' +
            'info@kya-energy.com<br>' +
            'N° RCCM : TG-LOM 2015 B 975<br>' +
            'NIF : 1000430317 | CNSS : 48863' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="kya-header-divider"></div>' +
      '<div class="kya-doc-number">N° <span class="kya-doc-name">' + docDisplay + '</span>' +
        (meta.ref ? ' &mdash; <span class="kya-doc-ref-inline">' + meta.ref + '</span>' : '') +
      '</div>';

    /* Toolbar Imprimer / PDF */
    var toolbar = document.createElement("div");
    toolbar.className = "kya-wf-toolbar";
    toolbar.innerHTML =
      '<button type="button" class="kya-btn-print" title="Imprimer">\u{1F5A8}️ Imprimer</button>' +
      '<button type="button" class="kya-btn-pdf" title="PDF">\u{1F4E5} PDF</button>';
    setTimeout(function () {
      var bp = toolbar.querySelector(".kya-btn-print");
      var bd = toolbar.querySelector(".kya-btn-pdf");
      if (bp) bp.addEventListener("click", printForm);
      if (bd) bd.addEventListener("click", printForm);
    }, 0);

    /* Bandeau circuit d'approbation */
    var info = document.createElement("div");
    info.className = "kya-wf-info";
    info.innerHTML =
      (meta.subtitle ? '<b>' + meta.subtitle + '</b> &mdash; ' : '') +
      'Circuit d’approbation : <b>' + meta.workflow + '</b>';

    /* Footer */
    var footer = document.createElement("div");
    footer.className = "kya-deco-footer kya-wf-footer";
    footer.innerHTML =
      '<strong class="kya-footer-brand">KYA-Energy Group</strong>' +
      ' | LOMÉ - TOGO | Tél. : +228 70 45 34 81' +
      '<span class="kya-footer-slogan">Move beyond the sky!</span>';

    /* Insertion : header + toolbar + info en haut, footer en bas */
    var anchor = formBody.firstChild;
    formBody.insertBefore(header, anchor);
    formBody.insertBefore(toolbar, anchor);
    formBody.insertBefore(info, anchor);
    formBody.appendChild(footer);

    formBody.classList.add("kya-decorated");

    /* Hide default Frappe header/intro */
    var defaultHead = document.querySelector(".web-form-head");
    if (defaultHead) defaultHead.classList.add("kya-hidden");
    var defaultIntro = document.querySelector(".web-form-introduction");
    if (defaultIntro) defaultIntro.style.display = "none";

    console.log("[KYA] Mode décoratif simple appliqué pour " + route);
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

    /* Mode DÉCORATIF SIMPLE pour les forms avec Table (cf. note plus haut) */
    if (DECORATIVE_ONLY_FORMS[route]) {
      buildDecorativeShell(route, meta, formBody);
      setupEmployeeAutoFill();
      setTimeout(function () {
        normalizeSignaturePads();
        setupSignaturePermissions(route);
        setupFieldEditPermissions(route);
      }, 600);
      return;
    }

    // Vérifier si le wrapper existe et contient SUFFISAMMENT de champs attendus.
    // Un wrapper construit trop tôt peut n'avoir qu'une fraction des champs
    // (les Link fields et Tables se montent après les Data fields simples).
    var existingWrapper = formBody.querySelector(".kya-sections-wrapper");
    if (existingWrapper) {
      var _allExp = [];
      sections.forEach(function(s) { s.fields.forEach(function(f) { _allExp.push(f); }); });
      var _inWrapper = _allExp.filter(function(fn) {
        return existingWrapper.querySelector('[data-fieldname="' + fn + '"]');
      }).length;
      if (_inWrapper >= Math.max(2, Math.ceil(_allExp.length * 0.55))) return; // OK
      existingWrapper.remove(); // reconstruit avec plus de champs disponibles
    }

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

    // Si aucun field trouvé (Frappe n'a pas encore monté les controls), on
    // n'écrit pas un wrapper vide — le prochain trigger (MutationObserver,
    // setTimeout, after_load) ré-essaiera quand les champs seront dans le DOM.
    if (Object.keys(allFields).length === 0) return;

    var wrapper = document.createElement("div");
    wrapper.className = "kya-sections-wrapper";

    /* === HEADER: 2-column Ordre de Mission style === */
    var docName = "";
    if (window.frappe && frappe.web_form_doc) {
      docName = frappe.web_form_doc.doc_name || frappe.web_form_doc.name || "";
    }
    // Si docName == slug de route (= nouveau formulaire), traiter comme PROVISOIRE
    if (docName && (docName === route || docName.toLowerCase() === route.toLowerCase())) {
      docName = "";
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

    setupWorkflowActions(wrapper);
    setTimeout(function() {
      normalizeSignaturePads();
      setupSignaturePermissions(route);
      setupFieldEditPermissions(route);
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
    var canSelectAny = canSelectAnyEmployee();

    function setInput(fieldName, value) {
      var el = findFieldEl(fieldName);
      if (!el) return;
      var input = el.querySelector("input");
      if (!input) return;
      input.value = value || "";
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function applyEmployee(emp) {
      if (!emp || !emp.name) return;
      setInput("employee", emp.name);
      setInput("employee_name", emp.employee_name);
      setInput("department", emp.department);
      if (emp.designation) setInput("designation", emp.designation);
    }

    function fetchEmployeeData(empId) {
      if (!empId || !window.frappe) return;
      frappe.call({
        method: "frappe.client.get_value",
        args: {
          doctype: "Employee",
          filters: { name: empId },
          fieldname: ["employee_name", "department", "designation"]
        },
        callback: function (r) {
          if (!r || !r.message) return;
          setInput("employee_name", r.message.employee_name);
          setInput("department", r.message.department);
          if (r.message.designation) setInput("designation", r.message.designation);
        }
      });
    }

    // ---- Recherche explicite par nom/matricule (pas d'auto-remplissage silencieux) ----
    function buildFuzzySearch() {
      if (empField.querySelector(".kya-fuzzy-wrap")) return;
      var wrap = document.createElement("div");
      wrap.className = "kya-fuzzy-wrap";
      wrap.style.cssText = "margin-top:6px;position:relative;";
      wrap.innerHTML =
        '<button type="button" class="kya-fuzzy-toggle" style="background:none;border:none;color:#0066cc;cursor:pointer;padding:0;font-size:0.85em;text-decoration:underline;">' +
        '🔍 Je ne connais pas mon ID / matricule</button>' +
        '<div class="kya-fuzzy-box" style="display:none;margin-top:6px;">' +
        '  <input type="text" class="form-control kya-fuzzy-input" placeholder="Tapez votre nom ou matricule…" autocomplete="off" />' +
        '  <ul class="kya-fuzzy-results" style="list-style:none;padding:0;margin:4px 0 0;border:1px solid #ddd;border-radius:4px;max-height:200px;overflow-y:auto;background:#fff;display:none;position:absolute;left:0;right:0;z-index:50;"></ul>' +
        '</div>';
      empField.appendChild(wrap);

      var toggle = wrap.querySelector(".kya-fuzzy-toggle");
      var box = wrap.querySelector(".kya-fuzzy-box");
      var input = wrap.querySelector(".kya-fuzzy-input");
      var results = wrap.querySelector(".kya-fuzzy-results");

      toggle.addEventListener("click", function () {
        var visible = box.style.display !== "none";
        box.style.display = visible ? "none" : "block";
        if (!visible) setTimeout(function () { input.focus(); }, 50);
      });

      var debounce = null;
      input.addEventListener("input", function () {
        var q = input.value.trim();
        if (debounce) clearTimeout(debounce);
        if (q.length < 2) {
          results.style.display = "none";
          results.innerHTML = "";
          return;
        }
        debounce = setTimeout(function () {
          frappe.call({
            method: canSelectAny ? "kya_hr.api.webform_helpers.search_employees" : "kya_hr.api.webform_helpers.find_my_employee",
            args: canSelectAny ? { query: q, limit: 10 } : { query: q },
            callback: function (r) {
              var rows = (r && r.message) || [];
              results.innerHTML = "";
              if (!rows.length) {
                results.innerHTML = '<li style="padding:8px;color:#888;">Aucune correspondance autorisée. Vérifiez votre saisie ou contactez la RH.</li>';
                results.style.display = "block";
                return;
              }
              rows.forEach(function (emp) {
                var li = document.createElement("li");
                li.style.cssText = "padding:8px;cursor:pointer;border-bottom:1px solid #eee;";
                li.innerHTML =
                  '<strong>' + (emp.employee_name || "") + '</strong> ' +
                  '<span style="color:#666;font-size:0.9em;">— ' + (emp.name || "") +
                  (emp.department ? ' · ' + emp.department : '') + '</span>';
                li.addEventListener("mouseenter", function () { li.style.background = "#f5f7fa"; });
                li.addEventListener("mouseleave", function () { li.style.background = ""; });
                li.addEventListener("click", function () {
                  applyEmployee(emp);
                  results.style.display = "none";
                  box.style.display = "none";
                });
                results.appendChild(li);
              });
              results.style.display = "block";
            }
          });
        }, 250);
      });

      // Ferme la liste si clic en dehors
      document.addEventListener("click", function (e) {
        if (!wrap.contains(e.target)) {
          results.style.display = "none";
        }
      });
    }
    buildFuzzySearch();

    // ---- Auto-fetch quand l'utilisateur tape un matricule ----------
    var obs = new MutationObserver(function () {
      var val = empInput.value;
      if (val && val.length > 3) fetchEmployeeData(val);
    });
    obs.observe(empInput, { attributes: true });
    empInput.addEventListener("change", function () { fetchEmployeeData(empInput.value); });
    lockEmployeeInputForSelfService();
  }

  /**
   * Fallback INLINE : quand `restructureForm` n'arrive pas à déplacer
   * les `.frappe-control` dans les sections (cas etat-recap, brouillard
   * où Frappe v16 re-monte les contrôles après notre appendChild), on
   * démolit le wrapper container et on bascule en mode "titres inline" :
   * - Le header KYA reste en haut du form
   * - Les titres de section sont insérés AVANT le premier champ de chaque section
   * - Les champs Frappe restent à leur position originale (= ne sont JAMAIS déplacés)
   * - Le footer reste en bas
   *
   * Pas de risque de "re-mount" Frappe car on ne touche plus aux .frappe-control.
   */
  function switchToInlineMode(wrapper, sections) {
    if (!wrapper || !sections) return;
    if (wrapper.dataset.kyaInlineSwitched === "1") return;

    var header = wrapper.querySelector(".kya-wf-header");
    var toolbar = wrapper.querySelector(".kya-wf-toolbar");
    var info = wrapper.querySelector(".kya-wf-info");
    var footer = wrapper.querySelector(".kya-wf-footer");

    var formBody = wrapper.parentNode;
    if (!formBody) return;

    // Détache les composants décoratifs du wrapper avant de le détruire
    [header, toolbar, info, footer].forEach(function (n) {
      if (n && n.parentNode === wrapper) wrapper.removeChild(n);
    });

    // Insère header + toolbar + info au TOP du formBody (avant tout le reste)
    var anchor = formBody.firstChild;
    [header, toolbar, info].forEach(function (n) {
      if (!n) return;
      formBody.insertBefore(n, anchor);
    });

    // Pour chaque section, insère un titre décoratif AVANT son 1er champ existant
    sections.forEach(function (sec, idx) {
      if (!sec.fields || !sec.fields.length) return;
      var firstFieldEl = null;
      for (var i = 0; i < sec.fields.length; i++) {
        firstFieldEl = findFieldEl(sec.fields[i]);
        if (firstFieldEl) break;
      }
      if (!firstFieldEl) return;

      var existing = document.querySelector(
        '.kya-inline-section[data-section-idx="' + idx + '"]'
      );
      if (existing) return; // déjà inséré

      var title = document.createElement("div");
      title.className = "kya-section-title kya-inline-section";
      title.setAttribute("data-section-idx", String(idx));
      title.innerHTML =
        '<span class="kya-section-icon">' + (sec.icon || "") + '</span> ' +
        (idx + 1) + ". " + sec.title;

      firstFieldEl.parentNode.insertBefore(title, firstFieldEl);
    });

    // Footer en bas
    if (footer) formBody.appendChild(footer);

    // Marque + supprime le wrapper container vide
    wrapper.dataset.kyaInlineSwitched = "1";
    if (wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);

    document.body.classList.add("kya-inline-mode");
    console.log("[KYA] Inline mode activé pour " + getRoute() + " (wrapper démoli)");
  }

  /**
   * Détecte si <30% des champs attendus sont dans le wrapper après build.
   * Si oui, bascule en mode INLINE (fallback robuste contre le re-mount Frappe v16).
   */
  function maybeFallbackToInlineMode() {
    var route = getRoute();
    var sections = FORM_SECTIONS[route];
    if (!sections) return false;

    var wrapper = document.querySelector(".kya-sections-wrapper");
    if (!wrapper) return false;

    var expected = [];
    sections.forEach(function (sec) {
      sec.fields.forEach(function (fn) { expected.push(fn); });
    });
    if (!expected.length) return false;

    var inWrapper = expected.filter(function (fn) {
      return wrapper.querySelector('[data-fieldname="' + fn + '"]');
    }).length;

    var ratio = inWrapper / expected.length;
    if (ratio < 0.30) {
      switchToInlineMode(wrapper, sections);
      return true;
    }
    return false;
  }

  /**
   * Déplace dans leurs sections les champs Frappe qui ont été montés
   * APRÈS la construction initiale du wrapper KYA (Table, Signatures,
   * Link fields lourds). Ne reconstruit PAS le wrapper, déplace juste
   * les `.frappe-control[data-fieldname=...]` orphelins.
   *
   * @returns {number} Nombre de champs déplacés (0 = rien à faire / tout déjà dans le wrapper).
   */
  function moveOrphanFieldsToSections() {
    var route = getRoute();
    var sections = FORM_SECTIONS[route];
    if (!sections) return 0;

    var wrapper = document.querySelector(".kya-sections-wrapper");
    if (!wrapper) return 0;

    // Récupère les body DOM des sections (dans l'ordre des sections)
    var sectionBodies = wrapper.querySelectorAll(".kya-section-body");
    if (!sectionBodies.length) return 0;

    // Build : fieldname -> { sectionIdx, gridClass }
    var fieldRouting = {};
    sections.forEach(function (sec, idx) {
      sec.fields.forEach(function (fn) {
        var gridClass = null;
        if (sec.grid && sec.grid[fn] === "span 2") gridClass = "kya-grid-span-2";
        else if (sec.grid && sec.grid[fn] === "col") gridClass = "kya-grid-col";
        fieldRouting[fn] = { sectionIdx: idx, gridClass: gridClass };
      });
    });

    var moved = 0;
    Object.keys(fieldRouting).forEach(function (fn) {
      var el = findFieldEl(fn);
      if (!el) return; // pas encore monté dans le DOM
      if (wrapper.contains(el)) return; // déjà dans le wrapper

      var routing = fieldRouting[fn];
      var body = sectionBodies[routing.sectionIdx];
      if (!body) return;

      if (routing.gridClass) el.classList.add(routing.gridClass);
      body.appendChild(el); // déplace (appendChild sur DOM existant = move)
      moved++;
    });

    return moved;
  }

  /**
   * Détecte si toutes les Tables (DataTable Frappe v16) du formulaire
   * sont entièrement montées dans le DOM. Frappe v16 a un comportement
   * particulier : monter une Table déclenche un re-render du form parent,
   * ce qui orpheline tout wrapper que l'on aurait construit avant.
   *
   * → On NE BUILD le wrapper QUE quand toutes les Tables sont stables.
   */
  function getExpectedTableFields(sections) {
    // Heuristique : fieldnames typiques de Tables KYA
    var tableNames = ["lignes", "items", "articles", "periodes", "presences"];
    var found = [];
    sections.forEach(function (sec) {
      sec.fields.forEach(function (fn) {
        if (tableNames.indexOf(fn) !== -1) found.push(fn);
      });
    });
    return found;
  }

  function allTablesMounted(tableFieldnames) {
    if (!tableFieldnames || tableFieldnames.length === 0) return true;
    return tableFieldnames.every(function (fn) {
      var el = findFieldEl(fn);
      if (!el) return false;
      // Une Table Frappe v16 monte : .frappe-control-table OU .grid-body OU table.table
      return !!el.querySelector(
        ".frappe-control-table, .grid-body, .form-grid, table.table"
      );
    });
  }

  function waitForForm() {
    var route = getRoute();
    if (!FORM_SECTIONS[route] && !FORM_META[route]) return;

    // Mode DÉCORATIF SIMPLE : ne touche pas aux champs Frappe, juste header + footer
    // Suffit d'un seul appel quand le formBody est dans le DOM
    if (DECORATIVE_ONLY_FORMS[route]) {
      var attempts0 = 0;
      var timer0 = setInterval(function () {
        var fb = document.querySelector(".web-form-wrapper") ||
                 document.querySelector(".web-form-body");
        if (fb || attempts0 >= 30) {
          clearInterval(timer0);
          if (fb) restructureForm();
        }
        attempts0++;
      }, 250);
      return;
    }

    // Construire la liste de tous les champs attendus pour ce formulaire
    var sections = FORM_SECTIONS[route] || [];
    var expectedFields = [];
    sections.forEach(function(sec) {
      sec.fields.forEach(function(fn) { expectedFields.push(fn); });
    });
    var expectedTables = getExpectedTableFields(sections);

    // Seuil : 55% des champs présents dans le DOM avant de construire le wrapper
    var minRequired = Math.max(2, Math.ceil(expectedFields.length * 0.55));

    function countReady() {
      return expectedFields.filter(function(fn) { return !!findFieldEl(fn); }).length;
    }

    function countInWrapper() {
      var w = document.querySelector(".kya-sections-wrapper");
      if (!w) return 0;
      return expectedFields.filter(function(fn) {
        return w.querySelector('[data-fieldname="' + fn + '"]');
      }).length;
    }

    function wrapperHasAllExpected() {
      return countInWrapper() >= expectedFields.length;
    }

    function tryBuild() {
      var hasWrapper = !!document.querySelector(".kya-sections-wrapper");
      if (!hasWrapper) {
        // Conditions pour build :
        //  1. ≥55% des champs montés
        //  2. TOUTES les Tables Frappe sont montées (sinon Frappe va re-render
        //     juste après notre build et orpheliner notre wrapper en haut,
        //     puis afficher son form natif en dessous → bug visuel du
        //     "wrapper en haut + form Desk en bas")
        if (countReady() >= minRequired && allTablesMounted(expectedTables)) {
          restructureForm();
          setupEmployeeAutoFill();
          setTimeout(normalizeSignaturePads, 700);
        }
      } else {
        // Wrapper déjà là : on déplace les champs orphelins (Signatures, Link
        // fields montés tardivement par Frappe v16) sans reconstruire.
        moveOrphanFieldsToSections();
      }
      // On garde le polling actif tant que tous les champs ne sont pas placés.
      return wrapperHasAllExpected();
    }

    if (tryBuild()) {
      installPostBuildObserver(expectedFields);
      return;
    }

    // Polling toutes les 350ms jusqu'à ~21s — couvre les Link fields et Tables
    // qui se montent après les champs Data simples (Frappe v16 mount async).
    // Le fallback INLINE n'est plus systématique (cf. directive user :
    // les autres web forms marchent en mode wrapper, ne pas forcer inline).
    var attempts = 0;
    var timer = setInterval(function() {
      attempts++;
      var done = tryBuild();
      if (done || attempts >= 60) {
        clearInterval(timer);
        installPostBuildObserver(expectedFields);
        // Au bout de 21s sans wrapper construit (Tables jamais montées?),
        // on tente quand même le build forcé + fallback inline si <30%
        if (!document.querySelector(".kya-sections-wrapper")) {
          console.warn("[KYA] Tables non montées après 21s, build forcé");
          if (countReady() >= 1) {
            restructureForm();
            setupEmployeeAutoFill();
            setTimeout(normalizeSignaturePads, 700);
            setTimeout(function () {
              try { maybeFallbackToInlineMode(); } catch (e) {}
            }, 2000);
          }
        }
      }
    }, 350);
  }

  /**
   * Planifie un check à 2.5s : si moins de 30% des champs ont été placés dans
   * les sections du wrapper, on bascule en mode INLINE (fallback robuste pour
   * les forms qui ont des Table / Signatures lourdes que Frappe v16 re-mount).
   */
  function scheduleInlineFallback() {
    setTimeout(function () {
      try { maybeFallbackToInlineMode(); } catch (e) { console.warn("[KYA] inline fallback failed", e); }
    }, 2500);
    // 2e tentative à 5s pour les forms très lents (Link fields multiples)
    setTimeout(function () {
      try { maybeFallbackToInlineMode(); } catch (e) {}
    }, 5000);
    // 3e ronde — masquage JS des sections vides (filet ultime indépendant de CSS :has())
    [1500, 3000, 5500, 9000].forEach(function (delay) {
      setTimeout(hideEmptyKyaSections, delay);
    });
  }

  /**
   * Filet de sécurité ultime : parcourt toutes les sections KYA construites
   * et cache (display:none) celles qui ne contiennent AUCUN champ Frappe.
   * Indépendant des règles CSS :has() qui peuvent ne pas s'appliquer.
   *
   * Cas couvert : etat-recap (et autres forms avec Table) où le wrapper est
   * construit mais les .frappe-control restent à leur place originale.
   */
  function hideEmptyKyaSections() {
    var sections = document.querySelectorAll(".kya-form-section");
    if (!sections.length) return;
    var hidden = 0;
    sections.forEach(function (sec) {
      // Considère "non vide" si la section contient au moins un de ces éléments :
      var hasContent = sec.querySelector(
        ".frappe-control, input.form-control, canvas, textarea, select, .grid-body, table.table"
      );
      if (!hasContent) {
        sec.style.display = "none";
        hidden++;
      } else {
        // Au cas où on avait masqué et que des champs sont apparus depuis
        if (sec.style.display === "none") sec.style.display = "";
      }
    });
    if (hidden > 0) {
      console.log("[KYA] " + hidden + " section(s) vide(s) masquée(s)");
    }
  }

  /**
   * Après le build initial, installe un MutationObserver sur le body :
   * dès qu'un `.frappe-control[data-fieldname]` apparaît hors du wrapper,
   * on le déplace dans sa section. Filet de sécurité pour Frappe v16 qui
   * re-monte parfois les champs après notre build.
   */
  function installPostBuildObserver(expectedFields) {
    if (window._kyaPostBuildObserver) return; // déjà installé
    var body = document.body;
    if (!body) return;

    var debounce = null;
    window._kyaPostBuildObserver = new MutationObserver(function () {
      if (debounce) clearTimeout(debounce);
      debounce = setTimeout(function () {
        var moved = moveOrphanFieldsToSections();
        if (moved > 0) {
          // Re-applique les permissions/visibilité après déplacement
          var route = getRoute();
          setupSignaturePermissions(route);
          setupFieldEditPermissions(route);
          normalizeSignaturePads();
        }
      }, 120);
    });
    window._kyaPostBuildObserver.observe(body, {
      childList: true,
      subtree: true,
    });

    // Stop l'observer après 30s (les champs lourds sont montés bien avant)
    setTimeout(function () {
      if (window._kyaPostBuildObserver) {
        window._kyaPostBuildObserver.disconnect();
        window._kyaPostBuildObserver = null;
      }
    }, 30000);
  }

  window.kyaRestructureForm = function () { restructureForm(); setupEmployeeAutoFill(); normalizeSignaturePads(); };
  window.kyaHideEmptySections = hideEmptyKyaSections; // exposé pour debug user
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function() { waitForForm(); setupAdminPreviewButton(); });
  } else {
    waitForForm(); setupAdminPreviewButton();
  }

  /* hideEmptyKyaSections retiré sur demande utilisateur (15/05/2026) :
   * "il faut faire les mêmes choses comme pour brouillard de caisse, pourquoi cacher ?"
   * → on garde la fonction exposée via window.kyaHideEmptySections() pour debug
   *   manuel, mais elle n'est plus appelée automatiquement. */
  if (window.frappe && window.frappe.ready) {
    frappe.ready(function () { setTimeout(waitForForm, 200); });
  }
  // Ré-initialiser à chaque navigation SPA
  if (window.frappe && window.frappe.router) {
    document.addEventListener("page-change", function () { setTimeout(waitForForm, 300); });
  }
  // Sécurité : si after_load du web form déclenche après notre polling
  document.addEventListener("frappe:web_form_loaded", function() { setTimeout(waitForForm, 100); });
  if (window.frappe && frappe.web_form) {
    var _origAfterLoad = frappe.web_form.after_load;
    frappe.web_form.after_load = function() {
      if (_origAfterLoad) _origAfterLoad.apply(this, arguments);
      setTimeout(waitForForm, 150);
    };
  }
})();
