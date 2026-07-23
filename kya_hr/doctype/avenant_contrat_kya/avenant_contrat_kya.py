# -*- coding: utf-8 -*-
"""Avenant au contrat de travail — généré dynamiquement par la RH.

Fortement variable (promotion / mutation / révision de rémunération…) : l'agent RH
renseigne les éléments (fonction, lieu, montants…), le corps par défaut est
pré-généré fidèlement au modèle KYA (visas, préambule, articles), PUIS la RH peut
tout éditer avant l'aperçu. Aucune reprise de code n'est nécessaire pour un nouvel
avenant : les visas et articles sont des listes librement éditables (JSON).
"""
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, today

from kya_hr.utils import nombre_en_lettres, date_fr
from kya_hr.utils.genre import accords, civilite_defaut


SIGNED_STATES = ("Signé", "Signée", "Émis")


def _montant(valeur):
    """« cent cinquante-trois mille cent treize (153 113) FCFA » à partir d'un nombre."""
    try:
        v = int(round(float(valeur)))
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return ""
    lettres = nombre_en_lettres(v, devise=None)
    return "{0} ({1}) FCFA".format(lettres, "{:,}".format(v).replace(",", " "))


class AvenantContratKYA(Document):
    def before_insert(self):
        self.autofill()
        if not self.date_document:
            self.date_document = today()
        if not (self.visas_json or self.articles_json):
            self.generer_corps(force=False)

    def validate(self):
        self._stamp_signatures()

    # Exposés au print format (le bac à sable Jinja n'expose pas frappe.parse_json).
    def get_visas(self):
        try:
            return json.loads(self.visas_json or "[]")
        except Exception:
            return []

    def get_articles(self):
        try:
            return json.loads(self.articles_json or "[]")
        except Exception:
            return []

    def fait_le(self):
        return date_fr(self.date_document)

    def autofill(self):
        if not self.employee:
            return
        emp = frappe.db.get_value(
            "Employee", self.employee,
            ["employee_name", "gender", "designation"], as_dict=True) or {}
        if not self.beneficiaire_nom:
            self.beneficiaire_nom = emp.get("employee_name")
        if not self.gender:
            self.gender = emp.get("gender")
        if not self.civilite:
            self.civilite = civilite_defaut(emp.get("gender"))

    # ── Génération du corps par défaut (fidèle au modèle, puis éditable) ──────
    def generer_corps(self, force=True):
        acc = accords(gender=self.gender, civilite=self.civilite)
        emp = acc["employe"]                    # « Employé » / « Employée »
        emp_min = acc["employe_min"]
        promue = acc["promu"]
        ref = self.ref_contrat or "……"

        visas = [
            "la Loi n° 2021-012 du 18 juin 2021 portant Code du travail togolais ;",
            "la Convention Collective Interprofessionnelle du Togo (CCIT) ;",
            "le contrat de travail {0} en cours d'exécution ;".format(ref),
        ]

        preambule = (
            "Le présent avenant est établi d'un commun accord, en application de l'article 11 "
            "de la CCIT qui subordonne toute modification substantielle du contrat (rémunération, "
            "lieu de travail, contenu du poste) à l'accord préalable des parties. Il est établi à "
            "la suite de la promotion de l'{emp}, en considération de son évolution professionnelle "
            "et de sa performance, et porte sur sa nouvelle fonction, son affectation et sa "
            "rémunération. Il est annexé au contrat de travail {ref} dont il fait partie intégrante."
        ).format(emp=emp, ref=ref)

        fonction = self.nouvelle_fonction or "……"
        lieu = self.nouveau_lieu or "……"
        pds = date_fr(self.date_prise_service) or "……"

        articles = []
        articles.append({
            "titre": "Article 1 — Nouvelle fonction et classification professionnelle",
            "corps": ("À compter de la date d'effet définie ci-après, l'{emp} est {promue} aux fonctions de "
                      "{fonction}. {Il} exerce ses fonctions sous l'autorité de la Direction Générale et "
                      "conserve l'intégralité de l'ancienneté acquise au titre du contrat de travail {ref}."
                      ).format(emp=emp, promue=promue, fonction=fonction, Il=acc["Il_Elle"], ref=ref),
        })
        articles.append({
            "titre": "Article 2 — Lieu de travail (mutation)",
            "corps": ("En application du présent avenant, le lieu de travail de l'{emp} est désormais fixé à "
                      "{lieu}. {Il} prendra effectivement service à son nouveau poste le {pds}. Un délai de "
                      "prévenance raisonnable lui est accordé pour organiser son installation."
                      ).format(emp=emp, lieu=lieu, Il=acc["Il_Elle"], pds=pds),
        })
        # Article 3 — rémunération (montants en lettres si fournis)
        rem_lignes = []
        if self.salaire_fixe:
            rem_lignes.append("- Part fixe : salaire de base fixé, conformément à la nouvelle grille salariale, "
                              "à {0}, payable mensuellement.".format(_montant(self.salaire_fixe)))
        if self.prime_affectation:
            rem_lignes.append("- Prime d'affectation : {0}, versée mensuellement. Elle couvre les primes de "
                              "fonction et d'hébergement et est attachée à l'exercice effectif de la fonction "
                              "visée à l'article 1.".format(_montant(self.prime_affectation)))
        rem_lignes.append("- Part variable : indexée sur le chiffre d'affaires et sur les performances "
                          "individuelles et collectives, perçue sur une base trimestrielle, selon les "
                          "modalités du guide de l'employé.")
        articles.append({
            "titre": "Article 3 — Rémunération",
            "corps": ("En application du présent avenant, la rémunération de l'{emp} comprend désormais une part "
                      "fixe, une prime de fonction et une part variable. Cette révision n'entraîne aucune "
                      "diminution de la rémunération globale antérieurement perçue.\n{lignes}"
                      ).format(emp=emp, lignes="\n".join(rem_lignes)),
        })
        if self.frais_installation:
            articles.append({
                "titre": "Article 4 — Frais d'installation, logement et transport liés à la mutation",
                "corps": ("- Frais d'installation : une indemnité d'installation de {0} est versée en une seule "
                          "fois au début de l'affectation, au titre du remboursement forfaitaire des frais "
                          "professionnels engagés à l'occasion de la mutation.\n"
                          "- Transport / déménagement : les frais de transport de l'{1} et de déménagement de "
                          "ses effets sont pris en charge par l'Employeur, sur justificatifs, dans les "
                          "conditions de l'article 34 de la CCIT.").format(_montant(self.frais_installation), emp_min),
            })
        articles.append({
            "titre": "Article — Maintien de l'ancienneté et des droits acquis",
            "corps": ("L'{emp} conserve l'ancienneté acquise au titre du contrat de travail {ref}. La présente "
                      "promotion et la mutation ne portent atteinte à aucun des droits acquis, sous réserve des "
                      "modifications expressément prévues par le présent avenant.").format(emp=emp, ref=ref),
        })
        articles.append({
            "titre": "Article — Dispositions non modifiées",
            "corps": ("Toutes les autres dispositions du contrat de travail {ref} non modifiées par le présent "
                      "avenant demeurent pleinement applicables et continuent de produire leurs effets."
                      ).format(ref=ref),
        })
        articles.append({
            "titre": "Article — Exemplaires et conservation",
            "corps": ("Le présent avenant est établi en trois (03) exemplaires originaux : un pour l'{emp}, un "
                      "pour l'Employeur et un destiné au dossier du personnel. Chaque page est paraphée par les "
                      "parties.").format(emp=emp),
        })

        if force or not self.preambule:
            self.preambule = preambule
        if force or not self.visas_json:
            self.visas_json = json.dumps(visas, ensure_ascii=False)
        if force or not self.articles_json:
            self.articles_json = json.dumps(articles, ensure_ascii=False)

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
        if self.signature_employe:
            self.signature_employe_finale = self.signature_employe
        if not self.date_signature:
            self.date_signature = now_datetime()

    def on_update_after_submit(self):
        self._notify_if_signed()

    def on_submit(self):
        self._notify_if_signed()

    def _notify_if_signed(self):
        if (self.workflow_state or "") not in SIGNED_STATES:
            return
        if self.flags.get("_notified"):
            return
        try:
            user = frappe.db.get_value("Employee", self.employee, "user_id") if self.employee else None
            if not user or user in ("Administrator", "Guest"):
                return
            frappe.sendmail(
                recipients=[user],
                subject="[KYA] Votre avenant au contrat est disponible",
                message=(
                    "<p>Bonjour,</p><p>Votre <b>avenant au contrat de travail</b> "
                    "({0}) a été signé par la Direction et est disponible.</p>"
                    "<p>— Ressources Humaines, KYA-Energy Group</p>"
                ).format(self.objet or self.name),
                reference_doctype=self.doctype, reference_name=self.name, now=False,
            )
            self.flags._notified = True
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Avenant KYA: notif")


# ── API page RH ───────────────────────────────────────────────────────────────
_RH_ROLES = {"Responsable RH", "HR Manager", "HR User", "Directeur Général", "DGA", "System Manager"}


def _guard():
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)
    if not _RH_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la RH et à la Direction."), frappe.PermissionError)


def _apply_champs(d, data):
    for k in ("num_avenant", "reference", "objet", "ref_contrat", "matricule_cnss",
              "domicile", "civilite", "nouvelle_fonction", "nouveau_lieu",
              "date_prise_service", "salaire_fixe", "prime_affectation",
              "frais_installation", "lieu", "date_effet", "date_document",
              "preambule", "visas_json", "articles_json"):
        if data.get(k) not in (None, ""):
            d.set(k, data.get(k))


@frappe.whitelist()
def apercu(data):
    """Rendu HTML de l'avenant tel qu'il sortira (aperçu live), sans enregistrer."""
    _guard()
    if isinstance(data, str):
        data = json.loads(data)
    if not data.get("employee"):
        return ""
    d = frappe.new_doc("Avenant Contrat KYA")
    d.employee = data["employee"]
    d.autofill()
    _apply_champs(d, data)
    if not d.date_document:
        d.date_document = today()
    if not (d.visas_json or d.articles_json):
        d.generer_corps(force=False)
    if int(data.get("utiliser_signature_enregistree") or 0):
        from kya_hr.kya_hr.doctype.document_rh_kya.document_rh_kya import signature_dg_data_uri
        d.signature_finale = signature_dg_data_uri() or None
    d.name = d.name or "APERÇU"
    from frappe.translate import print_language
    with print_language("fr"):
        return frappe.get_print("Avenant Contrat KYA", d.name, "Avenant Contrat KYA", doc=d)


@frappe.whitelist()
def generer_corps_defaut(data):
    """(Re)génère le corps par défaut (visas + préambule + articles) fidèle au
    modèle, à partir des éléments saisis, pour que la RH parte d'une base propre."""
    _guard()
    if isinstance(data, str):
        data = json.loads(data)
    d = frappe.new_doc("Avenant Contrat KYA")
    if data.get("employee"):
        d.employee = data["employee"]
        d.autofill()
    _apply_champs(d, data)
    d.generer_corps(force=True)
    return {"preambule": d.preambule, "visas_json": d.visas_json, "articles_json": d.articles_json}


@frappe.whitelist()
def creer(data):
    """Crée l'avenant (brouillon) depuis la page RH."""
    _guard()
    if isinstance(data, str):
        data = json.loads(data)
    if not data.get("employee") or not frappe.db.exists("Employee", data["employee"]):
        frappe.throw(_("Employé introuvable."))
    d = frappe.new_doc("Avenant Contrat KYA")
    d.employee = data["employee"]
    d.autofill()
    _apply_champs(d, data)
    d.utiliser_signature_enregistree = int(data.get("utiliser_signature_enregistree") or 0)
    d.insert()
    return {"name": d.name, "workflow_state": d.workflow_state or "Brouillon"}


@frappe.whitelist()
def liste(limit=60):
    _guard()
    from urllib.parse import quote
    rows = frappe.get_all(
        "Avenant Contrat KYA",
        fields=["name", "objet", "beneficiaire_nom", "employee", "workflow_state",
                "date_document", "modified"],
        order_by="modified desc", limit_page_length=int(limit or 60))
    for r in rows:
        r["pdf_url"] = ("/api/method/kya_hr.api.print_format.download_pdf"
                        "?doctype=Avenant%20Contrat%20KYA&name=" + quote(r["name"])
                        + "&format=Avenant%20Contrat%20KYA&language=fr")
    return rows
