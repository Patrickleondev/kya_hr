# -*- coding: utf-8 -*-
"""Contrat de stage d'immersion (découverte) — généré par la RH.

Fidèle au modèle KYA (texte légal citant le Code du travail togolais). Deux
variantes selon le garant : « Établissement » de formation ou « Tuteur Légal »
(diffèrent à l'article 7 — assurance — et au bloc de signature final). Accords en
genre pour le/la stagiaire. Multi-signataires (stagiaire « lu et approuvé »,
maître de stage, DG, garant). Cas de l'élève SANS e-mail : la RH remplit et
imprime, la signature se fait physiquement (aucune notification e-mail requise).
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, today

from kya_hr.utils import date_fr
from kya_hr.utils.genre import accords, civilite_defaut, est_feminin

SIGNED_STATES = ("Signé", "Signée", "Émis")


class ContratStageImmersionKYA(Document):
    def before_insert(self):
        self.autofill()
        if not self.date_document:
            self.date_document = today()

    def validate(self):
        if self.civilite and not self.gender:
            self.gender = "Female" if est_feminin(civilite=self.civilite) else "Male"
        if self.maitre_stage_employee and not self.maitre_stage_email:
            user_id = frappe.db.get_value("Employee", self.maitre_stage_employee, "user_id")
            if user_id:
                u = frappe.db.get_value("User", user_id, ["email", "enabled"], as_dict=True)
                if u and u.enabled:
                    self.maitre_stage_email = u.email
        self._stamp_signatures()

    def autofill(self):
        if not self.employee:
            return
        emp = frappe.db.get_value(
            "Employee", self.employee,
            ["employee_name", "gender", "cell_number", "personal_email",
             "company_email", "date_of_joining", "relieving_date"], as_dict=True) or {}
        if not self.beneficiaire_nom:
            self.beneficiaire_nom = emp.get("employee_name")
        if not self.gender:
            self.gender = emp.get("gender")
        if not self.civilite:
            self.civilite = civilite_defaut(emp.get("gender"))
        if not self.telephone:
            self.telephone = emp.get("cell_number")
        if not self.email:
            self.email = emp.get("personal_email") or emp.get("company_email")
        if not self.date_debut:
            self.date_debut = emp.get("date_of_joining")
        if not self.date_fin:
            self.date_fin = emp.get("relieving_date")

    # ── Exposés au print format ──────────────────────────────────────────────
    def acc(self):
        """Dict d'accords en genre pour le/la stagiaire."""
        return accords(gender=self.gender, civilite=self.civilite)

    def objectifs_list(self):
        return [l.strip() for l in (self.objectifs or "").split("\n") if l.strip()]

    def d_naissance(self):
        return date_fr(self.date_naissance)

    def d_debut(self):
        return date_fr(self.date_debut)

    def d_fin(self):
        return date_fr(self.date_fin)

    def fait_le(self):
        return date_fr(self.date_document)

    def maitre_designe(self):
        return "désignée" if self.maitre_stage_feminin else "désigné"

    # ── Signatures ────────────────────────────────────────────────────────────
    def _stamp_signatures(self):
        from kya_hr.kya_hr.doctype.document_rh_kya.document_rh_kya import signature_dg_data_uri
        state = self.workflow_state or ""
        if state not in SIGNED_STATES:
            self.signature_finale = None
            return
        if not self.utiliser_signature_enregistree and self.signature_dg:
            self.signature_finale = self.signature_dg
        else:
            self.signature_finale = signature_dg_data_uri() or None
        if self.signature_stagiaire:
            self.signature_stagiaire_finale = self.signature_stagiaire
        if not self.date_signature:
            self.date_signature = now_datetime()

    def on_update_after_submit(self):
        self._notify_if_signed()

    def on_submit(self):
        self._notify_if_signed()

    def on_update(self):
        self._notify_digital_transition()

    def _notify_digital_transition(self):
        """Circuit digital (28-29/07/2026) : stagiaire -> maître de stage ->
        garant (optionnel) -> RH prévenue quand prêt pour le DG. N'envoie
        qu'AU MOMENT de la transition (pas à chaque sauvegarde dans le même
        état), comme pour KYA Contrat."""
        before = self.get_doc_before_save()
        before_state = before.workflow_state if before else None
        if before_state == self.workflow_state:
            return
        try:
            from kya_hr.api.contrat_immersion_signature import notifier_transition
            notifier_transition(self, before_state)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Contrat Immersion KYA: notif digitale")

    def _notify_if_signed(self):
        """Notifie le/la stagiaire à la signature — SAUF s'il/elle est sans e-mail
        (case cochée) : dans ce cas la RH imprime et fait signer physiquement."""
        if (self.workflow_state or "") not in SIGNED_STATES:
            return
        if self.flags.get("_notified") or self.sans_email:
            return
        try:
            dest = self.email
            if not dest and self.employee:
                dest = frappe.db.get_value("Employee", self.employee, "user_id")
            if not dest or dest in ("Administrator", "Guest"):
                return
            acc = self.acc()
            frappe.sendmail(
                recipients=[dest],
                subject="[KYA] Votre contrat de stage d'immersion est disponible",
                message=(
                    "<p>Bonjour {nom},</p>"
                    "<p>Votre <b>contrat de stage d'immersion</b> ({ref}) a été signé par la "
                    "Direction de KYA-Energy Group.</p>"
                    "<p><b>Prochaines étapes :</b></p><ol>"
                    "<li>Prenez connaissance du contrat ci-joint / disponible auprès de la RH.</li>"
                    "<li>Apposez votre signature précédée de la mention manuscrite « lu et approuvé ».</li>"
                    "<li>Faites signer, le cas échéant, votre {garant}.</li>"
                    "<li>Remettez un exemplaire signé à la RH le premier jour du stage.</li>"
                    "</ol>"
                    "<p>Bon stage parmi nous !<br>— Ressources Humaines, KYA-Energy Group</p>"
                ).format(nom=self.beneficiaire_nom or "",
                         ref=self.name,
                         garant=("établissement" if self.type_garant == "Établissement" else "tuteur légal")),
                reference_doctype=self.doctype, reference_name=self.name, now=False,
            )
            self.flags._notified = True
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Contrat Immersion KYA: notif")


# ── API page RH ───────────────────────────────────────────────────────────────
_RH_ROLES = {"Responsable RH", "HR Manager", "HR User", "Directeur Général", "DGA",
             "System Manager", "Responsable des Stagiaires"}
_CHAMPS = ["civilite", "beneficiaire_nom", "date_naissance", "lieu_naissance",
           "nationalite", "piece_type", "piece_numero", "domicile", "pere", "mere",
           "telephone", "email", "etablissement", "num_certificat_scolarite",
           "type_garant", "etablissement_represente_par", "garant_nom",
           "garant_qualite", "garant_email", "objectifs",
           "duree_texte", "date_debut", "date_fin", "lieu_stage", "jour_debut",
           "jour_fin", "heure_debut", "heure_fin", "maitre_stage_nom",
           "maitre_stage_feminin", "maitre_stage_employee", "maitre_stage_email",
           "assurance_police", "assurance_compagnie",
           "rapport_delai_jours", "droit_image", "date_document", "lieu", "sans_email"]


def _guard():
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)
    if not _RH_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la RH et à la Direction."), frappe.PermissionError)


def _apply(d, data):
    if data.get("employee"):
        d.employee = data["employee"]
        d.autofill()
    for k in _CHAMPS:
        if data.get(k) not in (None, ""):
            d.set(k, data.get(k))


@frappe.whitelist()
def apercu(data):
    _guard()
    import json
    if isinstance(data, str):
        data = json.loads(data)
    d = frappe.new_doc("Contrat Stage Immersion KYA")
    _apply(d, data)
    if not d.beneficiaire_nom:
        d.beneficiaire_nom = "……………………"
    if not d.date_document:
        d.date_document = today()
    if d.civilite and not d.gender:
        d.gender = "Female" if est_feminin(civilite=d.civilite) else "Male"
    if int(data.get("utiliser_signature_enregistree") or 0):
        from kya_hr.kya_hr.doctype.document_rh_kya.document_rh_kya import signature_dg_data_uri
        d.signature_finale = signature_dg_data_uri() or None
    d.name = d.name or "APERÇU"
    from frappe.translate import print_language
    with print_language("fr"):
        return frappe.get_print("Contrat Stage Immersion KYA", d.name,
                                "Contrat Stage Immersion KYA", doc=d)


@frappe.whitelist()
def creer(data):
    _guard()
    import json
    if isinstance(data, str):
        data = json.loads(data)
    if not (data.get("beneficiaire_nom") or data.get("employee")):
        frappe.throw(_("Renseignez au moins le nom du/de la stagiaire."))
    d = frappe.new_doc("Contrat Stage Immersion KYA")
    _apply(d, data)
    d.utiliser_signature_enregistree = int(data.get("utiliser_signature_enregistree") or 0)
    d.insert()
    return {"name": d.name, "workflow_state": d.workflow_state or "Brouillon"}


@frappe.whitelist()
def liste(limit=60):
    _guard()
    from urllib.parse import quote
    rows = frappe.get_all(
        "Contrat Stage Immersion KYA",
        fields=["name", "beneficiaire_nom", "type_garant", "workflow_state",
                "date_document", "sans_email", "modified", "email",
                "garant_email", "signature_stagiaire", "signature_maitre",
                "signature_garant", "signature_finale"],
        order_by="modified desc", limit_page_length=int(limit or 60))
    for r in rows:
        r["signed"] = {
            "stagiaire": bool(r.pop("signature_stagiaire", None)),
            "maitre": bool(r.pop("signature_maitre", None)),
            "garant": bool(r.pop("signature_garant", None)),
            "dg": bool(r.pop("signature_finale", None)),
        }
        r["can_send_digital"] = (r["workflow_state"] in (None, "", "Brouillon")
                                  and not r["sans_email"] and bool(r.get("email")))
        r["pdf_url"] = ("/api/method/kya_hr.api.print_format.download_pdf"
                        "?doctype=Contrat%20Stage%20Immersion%20KYA&name=" + quote(r["name"])
                        + "&format=Contrat%20Stage%20Immersion%20KYA&language=fr")
    return rows


@frappe.whitelist()
def liste_stagiaires(q=None):
    """Employés/stagiaires pour le sélecteur (optionnel)."""
    _guard()
    rows = frappe.get_all("Employee", filters={"status": "Active"},
                          fields=["name", "employee_name", "employment_type"],
                          order_by="employee_name asc", limit_page_length=1000)
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in (r.employee_name or "").lower()]
    return rows
