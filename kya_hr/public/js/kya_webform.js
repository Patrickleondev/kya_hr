/* ===================================================================
   KYA-Energy Group — Web Form Layout v4
   Design : Ordre de Mission / Fiche officielle KYA
   En-tête 2-colonnes : Logo gauche | Titre + infos droite
   N° de document affiché, sections numérotées,
   permissions par rôle, signatures verrouillées.
   =================================================================== */

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
      ref: "KEG-RH-31-V01",
      workflow: "Ma\u00eetre de Stage \u2192 Resp. Stagiaires \u2192 Direction"
    },
    "permission-sortie-employe": {
      title: "DEMANDE DE PERMISSION DE SORTIE",
      subtitle: "Employ\u00e9",
      ref: "KEG-RH-30-V01",
      workflow: "Chef de Service \u2192 RH \u2192 Direction"
    },
    "demande-achat": {
      title: "FICHE D\u2019ENGAGEMENT DE D\u00c9PENSES",
      subtitle: "Approvisionnement",
      ref: "KEG-PRO-01-V01",
      workflow: "Chef \u2192 Auditeur \u2192 DAAF \u2192 DG"
    },
    "pv-sortie-materiel": {
      title: "PV DE SORTIE DE MAT\u00c9RIEL",
      subtitle: "Stock & Logistique",
      ref: "KEG-LOG-32-V01",
      workflow: "Chef \u2192 Audit \u2192 Direction \u2192 Magasin"
    },
    "planning-conge": {
      title: "PLANNING DE CONG\u00c9 ANNUEL",
      subtitle: "Ressources Humaines",
      ref: "KEG-RH-33-V01",
      workflow: "Employ\u00e9 \u2192 RH \u2192 DG"
    },
    "bilan-fin-de-stage": {
      title: "BILAN DE FIN DE STAGE",
      subtitle: "Formation & Stages",
      ref: "KEG-RH-34-V01",
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

  function waitForForm() {
    var route = getRoute();
    if (!FORM_SECTIONS[route] && !FORM_META[route]) return;
    var formReady = document.querySelector(".frappe-control") || document.querySelector("[data-fieldname]");
    if (formReady) { restructureForm(); setupEmployeeAutoFill(); return; }
    var obs = new MutationObserver(function (m, observer) {
      if (document.querySelector(".frappe-control") || document.querySelector("[data-fieldname]")) {
        observer.disconnect();
        setTimeout(function () { restructureForm(); setupEmployeeAutoFill(); }, 300);
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
    setTimeout(function () { if (!document.querySelector(".kya-form-section")) { restructureForm(); setupEmployeeAutoFill(); } }, 2000);
    setTimeout(function () { obs.disconnect(); if (!document.querySelector(".kya-form-section")) { restructureForm(); setupEmployeeAutoFill(); } }, 5000);
  }

  window.kyaRestructureForm = function () { restructureForm(); setupEmployeeAutoFill(); };
  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", function() { waitForForm(); setupAdminPreviewButton(); }); }
  else { waitForForm(); setupAdminPreviewButton(); }
  if (window.frappe && window.frappe.ready) { frappe.ready(function () { setTimeout(function() { waitForForm(); setupAdminPreviewButton(); }, 300); }); }
  if (window.frappe && window.frappe.router) { document.addEventListener("page-change", function () { setTimeout(waitForForm, 500); }); }
})();
