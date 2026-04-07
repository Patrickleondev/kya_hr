/* ===================================================================
   KYA-Energy Group ΓÇö Web Form Layout v4
   Design : Ordre de Mission / Fiche officielle KYA
   En-t├¬te 2-colonnes : Logo gauche | Titre + infos droite
   N┬░ de document affich├⌐, sections num├⌐rot├⌐es,
   permissions par r├┤le, signatures verrouill├⌐es.
   =================================================================== */

/* === Auto-redirect bare web form URLs to /new ==================== */
(function () {
  var KYA_WF_ROUTES = [
    "permission-sortie-stagiaire", "permission-sortie-employe",
    "demande-achat", "pv-sortie-materiel",
    "planning-conge", "bilan-fin-de-stage"
  ];
  var searchParams = new URLSearchParams(window.location.search || "");
  var docName = searchParams.get("name");
  var path = window.location.pathname.replace(/^\//, "").replace(/\/$/, "");
  var pathParts = path.split("/");

  // Frappe v16: ?name= URLs are NOT supported for authenticated users (server redirects to /new).
  // Convert ?name=<docname> → /{route}/{docname}/edit (Frappe canonical path format).
  if (pathParts.length === 1 && KYA_WF_ROUTES.indexOf(path) !== -1 && docName) {
    window.location.replace("/" + path + "/" + encodeURIComponent(docName) + "/edit");
    return;
  }

  // Path-based links like /{route}/{docname} work correctly in Frappe v16 — no conversion needed.
  // Sub-paths /new, /list, /edit are handled natively. Do NOT convert to ?name=.

  if (KYA_WF_ROUTES.indexOf(path) !== -1) {
    // Bare route without /new ΓÇö redirect silently
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
        fields: ["annee", "periodes"]
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
    ]
  };

  var FORM_META = {
    "permission-sortie-stagiaire": {
      title: "DEMANDE DE PERMISSION DE SORTIE",
      subtitle: "Stagiaire",
      ref: "AEA-ENG-30-V01",
      workflow: "Ma\u00eetre de Stage \u2192 Resp. Stagiaires \u2192 Direction"
    },
    "permission-sortie-employe": {
      title: "DEMANDE DE PERMISSION DE SORTIE",
      subtitle: "Employ\u00e9",
      ref: "AEA-ENG-30-V01",
      workflow: "Chef de Service \u2192 RH \u2192 Direction"
    },
    "demande-achat": {
      title: "FICHE D\u2019ENGAGEMENT DE D\u00c9PENSES",
      subtitle: "Approvisionnement",
      ref: "AEA-ENG-30-V01",
      workflow: "Chef \u2192 Auditeur \u2192 DAAF \u2192 DG"
    },
    "pv-sortie-materiel": {
      title: "PV DE SORTIE DE MAT\u00c9RIEL",
      subtitle: "Stock & Logistique",
      ref: "AEA-ENG-30-V01",
      workflow: "Chef \u2192 Audit \u2192 Direction \u2192 Magasin"
    },
    "planning-conge": {
      title: "PLANNING DE CONG\u00c9 ANNUEL",
      subtitle: "Ressources Humaines",
      ref: "AEA-ENG-30-V01",
      workflow: "Employ\u00e9 \u2192 RH \u2192 DG"
    },
    "bilan-fin-de-stage": {
      title: "BILAN DE FIN DE STAGE",
      subtitle: "Formation & Stages",
      ref: "AEA-ENG-30-V01",
      workflow: "Stagiaire \u2192 Encadrant \u2192 RH"
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
      signature_audit: ["DGA", "System Manager"],
      signature_dga: ["DGA", "DG", "System Manager"],
      signature_magasin: ["Stock Manager", "Stock User", "System Manager"]
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

  function injectVisibilityPatchCss() {
    if (document.getElementById("kya-wf-visibility-patch")) return;

    var style = document.createElement("style");
    style.id = "kya-wf-visibility-patch";
    style.textContent = [
      '/* Nuclear visibility fix ΓÇö inline <style> injected by kya_webform.js */',
      'select, select option { color: #1a1a2e !important; -webkit-text-fill-color: #1a1a2e !important; background-color: #fff !important; }',
      '.grid-heading-row, .grid-heading-row * { color: #1a1a2e !important; -webkit-text-fill-color: #1a1a2e !important; background: #eaf2f8 !important; }',
      '.grid-heading-row .static-area { color: #1a1a2e !important; font-weight: 700 !important; font-size: 11px !important; }',
      '.grid-heading-row .col, .grid-heading-row [data-fieldname] { color: #1a1a2e !important; opacity: 1 !important; }',
      '.rows *, .grid-row *, .no-value, .grid-body * { color: #1a1a2e !important; -webkit-text-fill-color: #1a1a2e !important; }',
      '.frappe-control[data-fieldtype="Signature"] .signature-field { min-height: 130px !important; height: 130px !important; }',
      '.frappe-control[data-fieldtype="Signature"] .signature-pad, .frappe-control[data-fieldtype="Signature"] canvas { min-height: 130px !important; height: 130px !important; max-height: 130px !important; }',
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
    var docName = frappe.web_form_doc.doc_name || frappe.web_form_doc.name;
    if (!docName) return;
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
      { label: "Permission Sortie Employ├⌐", route: "permission-sortie-employe" },
      { label: "Demande d'Achat", route: "demande-achat" },
      { label: "PV Sortie Mat├⌐riel", route: "pv-sortie-materiel" },
      { label: "Planning Cong├⌐", route: "planning-conge" },
      { label: "Bilan de Stage", route: "bilan-fin-de-stage" }
    ];
    var currentRoute = getRoute();
    var bar = document.createElement("div");
    bar.className = "kya-admin-preview-bar";
    var panel = document.createElement("div");
    panel.className = "kya-preview-panel";
    panel.style.display = "none";
    panel.innerHTML = '<h4>≡ƒöù Liens de pr├⌐visualisation</h4>' +
      '<div class="kya-preview-forms">' +
      allForms.map(function(f) {
        var url = window.location.origin + "/" + f.route + "/new";
        var isCurrent = f.route === currentRoute;
        return '<div class="kya-preview-form-link">' +
          '<span' + (isCurrent ? ' style="font-weight:800;"' : '') + '>' + f.label + '</span>' +
          '<a href="' + url + '" target="_blank">Ouvrir ΓåÆ</a>' +
          '</div>';
      }).join("") + '</div>' +
      '<button class="kya-preview-copy" onclick="(function(){var url=window.location.origin+\'/\'+\'' + currentRoute + '\'+\'/new\';navigator.clipboard&&navigator.clipboard.writeText(url).then(function(){this.textContent=\'Γ£ô Copi├⌐ !\';}.bind(this));}).call(this)">≡ƒôï Copier lien du formulaire actuel</button>';
    var toggle = document.createElement("button");
    toggle.className = "kya-preview-toggle";
    toggle.innerHTML = "≡ƒæü∩╕Å Aper├ºu Admin";
    toggle.addEventListener("click", function() {
      var vis = panel.style.display === "none";
      panel.style.display = vis ? "block" : "none";
      toggle.innerHTML = vis ? "Γ£ò Fermer" : "≡ƒæü∩╕Å Aper├ºu Admin";
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
    function fetchEmployeeData(empId) {
      if (!empId || !window.frappe) return;
      frappe.call({
        method: "frappe.client.get_value",
        args: { doctype: "Employee", filters: { name: empId }, fieldname: ["employee_name", "department"] },
        callback: function (r) {
          if (!r || !r.message) return;
          var nf = findFieldEl("employee_name");
          var df = findFieldEl("department");
          if (nf) { var ni = nf.querySelector("input"); if (ni) { ni.value = r.message.employee_name || ""; ni.dispatchEvent(new Event("change")); } }
          if (df) { var di = df.querySelector("input"); if (di) { di.value = r.message.department || ""; di.dispatchEvent(new Event("change")); } }
        }
      });
    }
    var obs = new MutationObserver(function () {
      var val = empInput.value;
      if (val && val.length > 3) fetchEmployeeData(val);
    });
    obs.observe(empInput, { attributes: true });
    empInput.addEventListener("change", function () { fetchEmployeeData(empInput.value); });
  }

  function forceSignatureFieldSize(el) {
    if (!el) return;
    var field = el.querySelector(".signature-field");
    var pad = el.querySelector(".signature-pad");
    var canvas = el.querySelector("canvas");
    var display = el.querySelector(".signature-display");
    var img = display ? display.querySelector("img") : null;

    if (field) {
      field.style.minHeight = "130px";
      field.style.height = "130px";
    }
    if (pad) {
      pad.style.minHeight = "130px";
      pad.style.height = "130px";
      pad.style.width = "100%";
    }
    if (canvas) {
      canvas.style.height = "130px";
      canvas.style.maxHeight = "130px";
      canvas.style.width = "100%";
    }
    if (display) {
      display.style.minHeight = "130px";
    }
    if (img) {
      img.style.maxHeight = "130px";
      img.style.width = "auto";
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

  function waitForForm() {
    var route = getRoute();
    injectVisibilityPatchCss();
    if (!FORM_SECTIONS[route] && !FORM_META[route]) return;
    var formReady = document.querySelector(".frappe-control") || document.querySelector("[data-fieldname]");
    if (formReady) {
      restructureForm();
      setupEmployeeAutoFill();
      stabilizeSignaturePads(route);
      setTimeout(forceInlineTextVisibility, 200);
      return;
    }
    var obs = new MutationObserver(function (m, observer) {
      if (document.querySelector(".frappe-control") || document.querySelector("[data-fieldname]")) {
        observer.disconnect();
        setTimeout(function () {
          restructureForm();
          setupEmployeeAutoFill();
          stabilizeSignaturePads(route);
          forceInlineTextVisibility();
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
    }, 2000);
    setTimeout(function () {
      obs.disconnect();
      if (!document.querySelector(".kya-form-section")) {
        restructureForm();
        setupEmployeeAutoFill();
      }
      stabilizeSignaturePads(route);
      forceInlineTextVisibility();
    }, 5000);
  }

  window.kyaRestructureForm = function () { restructureForm(); setupEmployeeAutoFill(); };
  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", function() { waitForForm(); setupAdminPreviewButton(); }); }
  else { waitForForm(); setupAdminPreviewButton(); }
  if (window.frappe && window.frappe.ready) { frappe.ready(function () { setTimeout(function() { waitForForm(); setupAdminPreviewButton(); }, 300); }); }
  if (window.frappe && window.frappe.router) { document.addEventListener("page-change", function () { setTimeout(waitForForm, 500); }); }
})();
