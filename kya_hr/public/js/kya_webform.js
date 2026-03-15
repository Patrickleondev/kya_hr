/* ═══════════════════════════════════════════════════════════
   KYA-Energy Group — Web Form Layout v3
   Style : Fiche d'Intervention (document officiel)
   Restructure Frappe web form fields into numbered sections,
   clean logo header, proper read-only styling, print support.
   ═══════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ── Section definitions per web-form route ───────────── */
  var FORM_SECTIONS = {
    "permission-sortie-stagiaire": [
      {
        title: "Informations du Stagiaire",
        icon: "👤",
        fields: ["employee", "employee_name", "department"],
        grid: { employee: "span 2", employee_name: "col", department: "col" },
      },
      {
        title: "Détails de la Sortie",
        icon: "🚪",
        fields: ["date_sortie", "heure_depart", "heure_retour", "motif", "justificatif"],
        grid: {
          date_sortie: "col",
          heure_depart: "col",
          heure_retour: "col",
          motif: "span 2",
          justificatif: "span 2",
        },
      },
      {
        title: "Validations & Signatures",
        icon: "✍️",
        fields: ["signature_stagiaire", "signature_chef", "signature_resp_stagiaires", "signature_dg"],
        sigGrid: true,
      },
    ],
    "permission-sortie-employe": [
      {
        title: "Informations de l'Employé",
        icon: "👤",
        fields: ["employee", "employee_name", "department"],
        grid: { employee: "span 2", employee_name: "col", department: "col" },
      },
      {
        title: "Détails de la Sortie",
        icon: "🚪",
        fields: [
          "date_sortie",
          "heure_depart",
          "heure_retour",
          "motif",
          "justificatif",
        ],
        grid: {
          date_sortie: "col",
          heure_depart: "col",
          heure_retour: "col",
          motif: "span 2",
          justificatif: "span 2",
        },
      },
      {
        title: "Validations & Signatures",
        icon: "✍️",
        fields: ["signature_employe", "signature_chef", "signature_rh", "signature_dga"],
        sigGrid: true,
      },
    ],
    "demande-achat": [
      {
        title: "Informations du Demandeur",
        icon: "👤",
        fields: ["employee", "employee_name", "department"],
        grid: { employee: "span 2", employee_name: "col", department: "col" },
      },
      {
        title: "Détails de la Demande",
        icon: "📋",
        fields: ["date_demande", "objet", "urgence"],
        grid: { date_demande: "col", urgence: "col", objet: "span 2" },
      },
      {
        title: "Articles Demandés",
        icon: "🛒",
        fields: ["items"],
      },
      {
        title: "Validations & Signatures",
        icon: "✍️",
        fields: ["signature_demandeur", "signature_chef", "signature_dga", "signature_dg"],
        sigGrid: true,
      },
    ],
    "pv-sortie-materiel": [
      {
        title: "Informations de la Sortie",
        icon: "📦",
        fields: ["objet", "date_sortie"],
        grid: { objet: "span 2", date_sortie: "span 2" },
      },
      {
        title: "Liste du Matériel",
        icon: "📝",
        fields: ["items", "demandeur_nom"],
      },
      {
        title: "Validations & Signatures",
        icon: "✍️",
        fields: ["signature_demandeur", "signature_audit", "signature_dga", "signature_magasin"],
        sigGrid: true,
      },
    ],
    "planning-conge": [
      {
        title: "Informations de l'Employé",
        icon: "👤",
        fields: ["employee", "employee_name", "department"],
        grid: { employee: "span 2", employee_name: "col", department: "col" },
      },
      {
        title: "Planning Annuel",
        icon: "📅",
        fields: ["annee", "periodes"],
      },
      {
        title: "Commentaire",
        icon: "💬",
        fields: ["commentaire_employe"],
      },
    ],
  };

  /* ── Form metadata ────────────────────────────────────── */
  var FORM_META = {
    "permission-sortie-stagiaire": {
      title: "DEMANDE DE PERMISSION DE SORTIE",
      subtitle: "Stagiaire",
      ref: "AEA-ENG-31-V01",
      workflow: "Maître de Stage → Resp. Stagiaires → Direction",
      desc: "Remplissez ce formulaire pour demander une permission de sortie.",
    },
    "permission-sortie-employe": {
      title: "DEMANDE DE PERMISSION DE SORTIE",
      subtitle: "Employé",
      ref: "AEA-ENG-30-V01",
      workflow: "Chef de Service → RH → Direction",
      desc: "Remplissez ce formulaire pour demander une permission de sortie.",
    },
    "demande-achat": {
      title: "FICHE D\u2019ENGAGEMENT DE D\u00c9PENSES",
      subtitle: "Approvisionnement",
      ref: "AEA-ENG-29-V01",
      workflow: "Chef → Auditeur → DAAF → DG",
      desc: "Soumettez votre demande d\u2019achat avec les articles n\u00e9cessaires.",
    },
    "pv-sortie-materiel": {
      title: "PV DE SORTIE DE MAT\u00c9RIEL",
      subtitle: "Stock & Logistique",
      ref: "AEA-ENG-32-V01",
      workflow: "Chef → Audit → Direction → Magasin",
      desc: "Enregistrez la sortie de mat\u00e9riel avec les articles concern\u00e9s.",
    },
    "planning-conge": {
      title: "PLANNING DE CONG\u00c9 ANNUEL",
      subtitle: "Ressources Humaines",
      ref: "AEA-ENG-33-V01",
      workflow: "Employ\u00e9 → RH → DG",
      desc: "Planifiez vos p\u00e9riodes de cong\u00e9 pour l\u2019ann\u00e9e.",
    },
  };

  /* ── Detect current route ─────────────────────────────── */
  function getRoute() {
    /* Prefer Frappe's web_form_doc.route (accurate even with /new suffix in URL) */
    if (window.frappe && frappe.web_form_doc && frappe.web_form_doc.route) {
      return frappe.web_form_doc.route;
    }
    /* Fallback: strip /new or /<docname> from pathname */
    var path = window.location.pathname.replace(/^\//, "").replace(/\/$/, "");
    return path.replace(/\/new$/, "").replace(/\/[^/]+$/, "");
  }

  /* ── Find field control by fieldname ──────────────────── */
  function findFieldEl(fieldname) {
    return (
      document.querySelector(
        '.frappe-control[data-fieldname="' + fieldname + '"]'
      ) || document.querySelector('[data-fieldname="' + fieldname + '"]')
    );
  }

  /* ── Create a numbered section ────────────────────────── */
  function createSection(cfg, idx) {
    var section = document.createElement("div");
    section.className = "kya-form-section";

    var header = document.createElement("div");
    header.className = "kya-section-title";
    header.innerHTML =
      '<span class="kya-section-icon">' +
      (cfg.icon || "") +
      "</span> " +
      idx +
      ". " +
      cfg.title;
    section.appendChild(header);

    var body = document.createElement("div");
    body.className = "kya-section-body";
    if (cfg.sigGrid) {
      body.classList.add("kya-sig-grid");
    } else if (cfg.grid) {
      body.classList.add("kya-grid");
    }
    section.appendChild(body);

    return { section: section, body: body };
  }

  /* ── Print function ───────────────────────────────────── */
  function printForm() {
    window.print();
  }

  /* ── Download as PDF (browser print-to-PDF) ───────────── */
  function downloadPDF() {
    window.print();
  }

  /* ── Workflow Action Toolbar (Mobile Approval) ────────── */
  function setupWorkflowActions(wrapper) {
    if (!window.frappe || !frappe.web_form_doc) return;
    var docName = frappe.web_form_doc.doc_name || frappe.web_form_doc.name;
    if (!docName) return; /* New form — no actions */
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

        /* State badge */
        var stateEl = document.createElement("div");
        stateEl.className = "kya-wf-state";
        var stateClass = "kya-state-pending";
        var ws = data.workflow_state || "";
        if (ws === "Approuvé" || ws === "Approuvée") stateClass = "kya-state-approved";
        else if (ws === "Rejeté" || ws === "Rejetée") stateClass = "kya-state-rejected";
        else if (ws === "Brouillon") stateClass = "kya-state-draft";
        stateEl.innerHTML =
          '<span class="kya-state-label">État :</span> ' +
          '<span class="kya-state-badge ' + stateClass + '">' + ws + '</span>';

        /* Action buttons */
        if (actions.length) {
          var btnContainer = document.createElement("div");
          btnContainer.className = "kya-wf-actions";
          actions.forEach(function (a) {
            var btn = document.createElement("button");
            btn.type = "button";
            var isReject = /rejeter|refuser/i.test(a.action);
            btn.className = isReject ? "kya-btn-reject" : "kya-btn-approve";
            btn.textContent = a.action;
            btn.title = "→ " + a.next_state;
            btn.addEventListener("click", function () {
              applyWorkflowAction(doctype, docName, a.action, a.next_state);
            });
            btnContainer.appendChild(btn);
          });
          stateEl.appendChild(btnContainer);
        }

        /* Insert after toolbar or header */
        var toolbar = wrapper.querySelector(".kya-wf-toolbar");
        if (toolbar) {
          toolbar.parentNode.insertBefore(stateEl, toolbar.nextSibling);
        } else {
          var header = wrapper.querySelector(".kya-wf-header");
          if (header) {
            header.parentNode.insertBefore(stateEl, header.nextSibling);
          }
        }
      },
    });
  }

  function applyWorkflowAction(doctype, docname, action, nextState) {
    if (!confirm("Confirmer l\u2019action : " + action + " ?\n(→ " + nextState + ")")) {
      return;
    }
    frappe.call({
      method: "kya_hr.api.apply_kya_workflow_action",
      args: { doctype: doctype, docname: docname, action: action },
      callback: function (r) {
        if (r && r.message && r.message.status === "success") {
          frappe.msgprint({
            title: "Action effectuée",
            message: "Le document est maintenant : <b>" + r.message.workflow_state + "</b>",
            indicator: "green",
          });
          setTimeout(function () { window.location.reload(); }, 1500);
        }
      },
      error: function () {
        frappe.msgprint({
          title: "Erreur",
          message: "Impossible d\u2019effectuer cette action. V\u00e9rifiez vos permissions.",
          indicator: "red",
        });
      },
    });
  }

  /* ── Main restructure function ────────────────────────── */
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

    /* Already restructured? */
    if (formBody.querySelector(".kya-form-section")) return;

    /* Remove any existing kya-wf-header from introduction_text to avoid duplicates */
    var existingHeaders = document.querySelectorAll(
      ".introduction .kya-wf-header, .web-form-header .kya-wf-header"
    );
    existingHeaders.forEach(function (h) {
      h.parentNode.removeChild(h);
    });
    /* Also remove existing kya-wf-info from introduction_text */
    var existingInfos = document.querySelectorAll(
      ".introduction .kya-wf-info, .web-form-header .kya-wf-info"
    );
    existingInfos.forEach(function (h) {
      h.parentNode.removeChild(h);
    });

    /* Collect fields */
    var allFields = {};
    var assigned = {};
    sections.forEach(function (sec) {
      sec.fields.forEach(function (fn) {
        var el = findFieldEl(fn);
        if (el) allFields[fn] = el;
      });
    });

    /* Build wrapper */
    var wrapper = document.createElement("div");
    wrapper.className = "kya-sections-wrapper";

    /* ── Clean header (like Fiche d'Intervention) ──────── */
    var header = document.createElement("div");
    header.className = "kya-wf-header";
    header.innerHTML =
      '<div class="kya-header-top">' +
        '<div class="kya-header-info">' +
          '<span>N\u00b0 RCCM : TG-LOM 2015 B 975</span>' +
          '<span>NIF : 1000430317</span>' +
        '</div>' +
      '</div>' +
      '<img class="kya-logo" src="/assets/kya_hr/images/logo_kya.png" ' +
      'alt="KYA-Energy Group" onerror="this.src=\'/files/vrai.png\'">' +
      "<h3>" +
      meta.title +
      "</h3>" +
      (meta.ref
        ? '<span class="kya-doc-ref">' + meta.ref + "</span>"
        : "") +
      '<span class="kya-slogan">Move beyond the sky!</span>' +
      (meta.subtitle
        ? '<span class="kya-subtitle">' + meta.subtitle + "</span>"
        : "");
    wrapper.appendChild(header);

    /* ── Toolbar: print / download ─────────────────────── */
    var toolbar = document.createElement("div");
    toolbar.className = "kya-wf-toolbar";
    toolbar.innerHTML =
      '<button type="button" class="kya-btn-print" title="Imprimer">🖨️ Imprimer</button>' +
      '<button type="button" class="kya-btn-pdf" title="Télécharger PDF">📥 PDF</button>';
    wrapper.appendChild(toolbar);

    /* Bind toolbar events */
    setTimeout(function () {
      var btnPrint = toolbar.querySelector(".kya-btn-print");
      var btnPdf = toolbar.querySelector(".kya-btn-pdf");
      if (btnPrint) btnPrint.addEventListener("click", printForm);
      if (btnPdf) btnPdf.addEventListener("click", downloadPDF);
    }, 0);

    /* ── Info box ──────────────────────────────────────── */
    var info = document.createElement("div");
    info.className = "kya-wf-info";
    info.innerHTML =
      "<b>" +
      meta.desc +
      "</b><br>" +
      "Circuit d\u2019approbation : <b>" +
      meta.workflow +
      "</b>";
    wrapper.appendChild(info);

    /* ── Build numbered sections and move fields ────────── */
    var sectionIdx = 0;
    sections.forEach(function (sec) {
      sectionIdx++;
      var s = createSection(sec, sectionIdx);
      sec.fields.forEach(function (fn) {
        var el = allFields[fn];
        if (!el) return;
        assigned[fn] = true;
        if (sec.grid && sec.grid[fn] === "span 2") {
          el.classList.add("kya-grid-span-2");
        } else if (sec.grid && sec.grid[fn] === "col") {
          el.classList.add("kya-grid-col");
        }
        s.body.appendChild(el);
      });
      wrapper.appendChild(s.section);
    });

    /* ── Footer ────────────────────────────────────────── */
    var footer = document.createElement("div");
    footer.className = "kya-wf-footer";
    footer.innerHTML =
      '<strong class="kya-footer-brand">KYA-Energy Group</strong>' +
      " | LOM\u00c9 - TOGO | T\u00e9l. : +228 70 45 34 81" +
      '<span class="kya-footer-slogan">Move beyond the sky!</span>';
    wrapper.appendChild(footer);

    /* Insert wrapper at top of form body */
    var firstChild = formBody.firstChild;
    if (firstChild) {
      formBody.insertBefore(wrapper, firstChild);
    } else {
      formBody.appendChild(wrapper);
    }

    formBody.classList.add("kya-restructured");

    /* ── Workflow action toolbar (mobile approval) ─────── */
    setupWorkflowActions(wrapper);

    /* ── Hide default Frappe web-form header ───────────── */
    var defaultHead = document.querySelector(".web-form-head");
    if (defaultHead) defaultHead.classList.add("kya-hidden");
    var defaultIntro = document.querySelector(".web-form-introduction");
    if (defaultIntro) defaultIntro.style.display = "none";

    /* ── Mark read-only fields with data attribute ──────── */
    var readOnlyFields = ["employee_name", "department", "designation"];
    readOnlyFields.forEach(function (fn) {
      var el = findFieldEl(fn);
      if (el) el.setAttribute("data-read-only", "1");
    });
  }

  /* ── Auto-fill employee_name and department ───────────── */
  function setupEmployeeAutoFill() {
    var route = getRoute();
    if (!FORM_SECTIONS[route]) return;

    /* Watch for employee Link field value changes */
    var empField = findFieldEl("employee");
    if (!empField) return;

    var empInput = empField.querySelector("input");
    if (!empInput) return;

    function fetchEmployeeData(empId) {
      if (!empId || !window.frappe) return;
      frappe.call({
        method: "frappe.client.get_value",
        args: {
          doctype: "Employee",
          filters: { name: empId },
          fieldname: ["employee_name", "department"],
        },
        callback: function (r) {
          if (r && r.message) {
            var nameField = findFieldEl("employee_name");
            var deptField = findFieldEl("department");
            if (nameField) {
              var nameInput = nameField.querySelector("input");
              if (nameInput) {
                nameInput.value = r.message.employee_name || "";
                nameInput.dispatchEvent(new Event("change"));
              }
            }
            if (deptField) {
              var deptInput = deptField.querySelector("input");
              if (deptInput) {
                deptInput.value = r.message.department || "";
                deptInput.dispatchEvent(new Event("change"));
              }
            }
          }
        },
      });
    }

    /* Listen for changes on the employee input */
    var observer = new MutationObserver(function () {
      var val = empInput.value;
      if (val && val.length > 3) {
        fetchEmployeeData(val);
      }
    });
    observer.observe(empInput, { attributes: true });

    empInput.addEventListener("change", function () {
      fetchEmployeeData(empInput.value);
    });
  }

  /* ── Observer: wait for form fields to be rendered ────── */
  function waitForForm() {
    var route = getRoute();
    if (!FORM_SECTIONS[route] && !FORM_META[route]) return;

    /* V16: Check multiple possible selectors */
    var formReady =
      document.querySelector(".frappe-control") ||
      document.querySelector(".web-form-body .frappe-control") ||
      document.querySelector('[data-fieldname]');

    if (formReady) {
      restructureForm();
      setupEmployeeAutoFill();
      return;
    }

    var obs = new MutationObserver(function (mutations, observer) {
      var ready =
        document.querySelector(".frappe-control") ||
        document.querySelector('[data-fieldname]');
      if (ready) {
        observer.disconnect();
        setTimeout(function () {
          restructureForm();
          setupEmployeeAutoFill();
        }, 300);
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });

    /* Fallback: try after 2s and 5s even if observer doesn't trigger */
    setTimeout(function () {
      if (!document.querySelector(".kya-form-section")) {
        restructureForm();
        setupEmployeeAutoFill();
      }
    }, 2000);

    setTimeout(function () {
      obs.disconnect();
      if (!document.querySelector(".kya-form-section")) {
        restructureForm();
        setupEmployeeAutoFill();
      }
    }, 5000);
  }

  /* ── Init ──────────────────────────────────────────────── */
  /* Expose for V16 client_script triggers */
  window.kyaRestructureForm = function () {
    restructureForm();
    setupEmployeeAutoFill();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function() {
      waitForForm();
    });
  } else {
    waitForForm();
  }

  /* V16: frappe.ready triggers after Vue rendering */
  if (window.frappe && window.frappe.ready) {
    frappe.ready(function () {
      setTimeout(waitForForm, 300);
    });
  }

  if (window.frappe && window.frappe.router) {
    document.addEventListener("page-change", function () {
      setTimeout(waitForForm, 500);
    });
  }
})();
