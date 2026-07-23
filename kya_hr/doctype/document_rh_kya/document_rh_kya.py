# -*- coding: utf-8 -*-
"""Document RH KYA — certificats & attestations générés dynamiquement.

Un seul DocType pour trois rendus (Certificat de Stage, Attestation de Travail,
Attestation de Prestation). La RH crée depuis la fiche employé/stagiaire, les
champs variables sont pré-remplis puis éditables ; le circuit RH → DG appose la
signature (image enregistrée du DG estampillée, OU signature en ligne).
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, today


_MOIS_LETTRES = {
    1: "un (01) mois", 2: "deux (02) mois", 3: "trois (03) mois",
    4: "quatre (04) mois", 5: "cinq (05) mois", 6: "six (06) mois",
    7: "sept (07) mois", 8: "huit (08) mois", 9: "neuf (09) mois",
    10: "dix (10) mois", 11: "onze (11) mois", 12: "douze (12) mois",
}


def duree_en_lettres(date_debut, date_fin):
    """Durée lisible entre deux dates : « trois (03) mois » si multiple de mois,
    sinon « N jour(s) ». Renvoie '' si dates manquantes."""
    if not date_debut or not date_fin:
        return ""
    d1, d2 = getdate(date_debut), getdate(date_fin)
    if d2 < d1:
        return ""
    jours = date_diff(d2, d1) + 1
    mois = round(jours / 30.0)
    if 1 <= mois <= 12 and abs(jours - mois * 30) <= 5:
        return _MOIS_LETTRES[mois]
    return "{0} jour{1}".format(jours, "s" if jours > 1 else "")


class DocumentRHKYA(Document):
    def before_insert(self):
        self.autofill()
        if not self.date_document:
            self.date_document = today()

    SIGNED_STATES = ("Signé", "Signée", "Émis")

    def validate(self):
        # Durée recalculée si vide (l'agent RH peut l'écraser).
        if not self.duree_texte and self.date_debut and self.date_fin:
            self.duree_texte = duree_en_lettres(self.date_debut, self.date_fin)
        self._stamp_signature()

    def _stamp_signature(self):
        """Résout la signature à afficher UNE fois le document signé par le DG :
        signature en ligne si fournie, sinon l'image enregistrée du DG. Rien tant
        que le circuit n'est pas au stade signé (aucune signature sur un brouillon)."""
        state = self.workflow_state or ""
        if state not in self.SIGNED_STATES:
            # tant que non signé : pas de signature (évite qu'un brouillon paraisse signé)
            self.signature_finale = None
            if not self.is_new():
                self.date_signature = None
            return
        sig = ""
        if not self.utiliser_signature_enregistree and self.signature_dg:
            sig = self.signature_dg
        else:
            sig = signature_dg_data_uri()
        self.signature_finale = sig or None
        if not self.date_signature:
            from frappe.utils import now_datetime
            self.date_signature = now_datetime()

    def autofill(self):
        """Pré-remplit les champs variables depuis la fiche Employee (éditable ensuite)."""
        if not self.employee:
            return
        emp = frappe.db.get_value(
            "Employee", self.employee,
            ["employee_name", "gender", "cell_number", "personal_email",
             "company_email", "designation", "date_of_joining", "relieving_date"],
            as_dict=True) or {}
        if not self.beneficiaire_nom:
            self.beneficiaire_nom = emp.get("employee_name")
        if not self.civilite:
            self.civilite = "Mme" if (emp.get("gender") == "Female") else "M."
        if not self.telephone:
            self.telephone = emp.get("cell_number")
        if not self.email:
            self.email = emp.get("personal_email") or emp.get("company_email")
        if not self.poste:
            self.poste = emp.get("designation")
        if not self.date_debut:
            self.date_debut = emp.get("date_of_joining")
        if not self.date_fin:
            self.date_fin = emp.get("relieving_date")
        if not self.duree_texte:
            self.duree_texte = duree_en_lettres(self.date_debut, self.date_fin)


@frappe.whitelist()
def prefill_from_employee(employee, type_document=None):
    """Renvoie les champs pré-remplis pour un employé (page RH + formulaire)."""
    if not employee or not frappe.db.exists("Employee", employee):
        return {}
    emp = frappe.db.get_value(
        "Employee", employee,
        ["employee_name", "gender", "cell_number", "personal_email",
         "company_email", "designation", "date_of_joining", "relieving_date"],
        as_dict=True) or {}
    return {
        "beneficiaire_nom": emp.get("employee_name"),
        "civilite": "Mme" if emp.get("gender") == "Female" else "M.",
        "telephone": emp.get("cell_number"),
        "email": emp.get("personal_email") or emp.get("company_email"),
        "poste": emp.get("designation"),
        "date_debut": emp.get("date_of_joining"),
        "date_fin": emp.get("relieving_date"),
        "duree_texte": duree_en_lettres(emp.get("date_of_joining"), emp.get("relieving_date")),
        "nationalite": "togolaise",
    }


def signature_dg_data_uri():
    """Signature enregistrée du DG (data URI) depuis le Single « Signature Direction
    KYA », prête pour le print format. '' si non configurée."""
    try:
        sig = frappe.db.get_single_value("Signature Direction KYA", "signature")
    except Exception:
        sig = None
    if not sig:
        return ""
    if str(sig).startswith("data:"):
        return sig
    # Fichier attaché (/files/..) → data URI
    try:
        import base64
        from frappe.utils.file_manager import get_file
        _name, content = get_file(sig)
        if isinstance(content, str):
            content = content.encode("latin-1", errors="ignore")
        ext = (sig.rsplit(".", 1)[-1] or "png").lower()
        mime = "image/png" if ext == "png" else ("image/jpeg" if ext in ("jpg", "jpeg") else "image/png")
        return "data:%s;base64,%s" % (mime, base64.b64encode(content).decode())
    except Exception:
        return ""
