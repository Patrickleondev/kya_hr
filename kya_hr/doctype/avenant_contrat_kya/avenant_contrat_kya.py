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
        if not (self.visas or self.get("articles")):
            self.generer_corps(force=False)

    def validate(self):
        self._stamp_signatures()

    # Exposés au print format.
    def get_visas(self):
        return [l.strip() for l in (self.visas or "").split("\n") if l.strip()]

    def get_articles(self):
        return [{"titre": a.titre, "corps": a.corps} for a in (self.articles or [])]

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
        """Pré-remplit VU + préambule + articles fidèles au modèle KYA. Le corps
        des articles est du HTML (gras/puces natifs), directement éditable ensuite
        par la RH dans la grille. Réservé à la promotion/mutation/rémunération ;
        la RH peut ajouter/retirer des articles pour tout autre objet."""
        acc = accords(gender=self.gender, civilite=self.civilite)
        emp = acc["employe"]                    # « Employé » / « Employée »
        emp_min = acc["employe_min"]
        promue = acc["promu"]
        ref = self.ref_contrat or "……"
        fonction = self.nouvelle_fonction or "……"
        lieu = self.nouveau_lieu or "……"
        pds = date_fr(self.date_prise_service) or "……"

        def P(t):
            return "<p>{0}</p>".format(t)

        def UL(items):
            return "<ul>" + "".join("<li>{0}</li>".format(i) for i in items) + "</ul>"

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

        articles = []
        articles.append(("Article 1 — Nouvelle fonction et classification professionnelle",
            P("À compter de la date d'effet définie ci-après, l'{emp} est {promue} aux fonctions de "
              "{fonction}. {Il} exerce ses fonctions sous l'autorité de la Direction Générale et conserve "
              "l'intégralité de l'ancienneté acquise au titre du contrat de travail {ref}."
              ).format(emp=emp, promue=promue, fonction=fonction, Il=acc["Il_Elle"], ref=ref)))
        articles.append(("Article 2 — Lieu de travail (mutation)",
            P("En application du présent avenant, le lieu de travail de l'{emp} est désormais fixé à {lieu}. "
              "{Il} prendra effectivement service à son nouveau poste le {pds}. Un délai de prévenance "
              "raisonnable lui est accordé pour organiser son installation."
              ).format(emp=emp, lieu=lieu, Il=acc["Il_Elle"], pds=pds)))
        # Article 3 — rémunération (montants en lettres si fournis, en gras)
        rem = []
        if self.salaire_fixe:
            rem.append("<b>Part fixe :</b> salaire de base fixé, conformément à la nouvelle grille "
                       "salariale, <b>à {0}</b>, payable mensuellement.".format(_montant(self.salaire_fixe)))
        if self.prime_affectation:
            rem.append("<b>Prime d'affectation : {0}</b>, versée mensuellement. Elle couvre les primes de "
                       "fonction et d'hébergement et est attachée à l'exercice effectif de la fonction visée "
                       "à l'article 1.".format(_montant(self.prime_affectation)))
        rem.append("<b>Part variable :</b> indexée sur le chiffre d'affaires et sur les performances "
                   "individuelles et collectives, perçue sur une base trimestrielle, selon les modalités du "
                   "guide de l'employé.")
        articles.append(("Article 3 — Rémunération",
            P("En application du présent avenant, la rémunération de l'{emp} comprend désormais une part fixe, "
              "une prime de fonction et une part variable. Cette révision n'entraîne aucune diminution de la "
              "rémunération globale antérieurement perçue.".format(emp=emp)) + UL(rem)))
        if self.frais_installation:
            articles.append(("Article 4 — Frais d'installation, logement et transport liés à la mutation",
                UL(["<b>Frais d'installation :</b> une indemnité d'installation de <b>{0}</b> est versée en une "
                    "seule fois au début de l'affectation, au titre du remboursement forfaitaire des frais "
                    "professionnels engagés à l'occasion de la mutation.".format(_montant(self.frais_installation)),
                    "<b>Transport / déménagement :</b> les frais de transport de l'{0} et de déménagement de ses "
                    "effets sont pris en charge par l'Employeur, sur justificatifs, dans les conditions de "
                    "l'article 34 de la CCIT.".format(emp_min)])))
        articles.append(("Article — Maintien de l'ancienneté et des droits acquis",
            P("L'{emp} conserve l'ancienneté acquise au titre du contrat de travail {ref}. La présente promotion "
              "et la mutation ne portent atteinte à aucun des droits acquis, sous réserve des modifications "
              "expressément prévues par le présent avenant.").format(emp=emp, ref=ref)))
        articles.append(("Article — Dispositions non modifiées",
            P("Toutes les autres dispositions du contrat de travail {ref} non modifiées par le présent avenant "
              "demeurent pleinement applicables et continuent de produire leurs effets.").format(ref=ref)))
        articles.append(("Article — Exemplaires et conservation",
            P("Le présent avenant est établi en trois (03) exemplaires originaux : un pour l'{emp}, un pour "
              "l'Employeur et un destiné au dossier du personnel. Chaque page est paraphée par les parties."
              ).format(emp=emp)))

        if force or not self.preambule:
            self.preambule = preambule
        if force or not (self.visas or "").strip():
            self.visas = "\n".join(visas)
        if force or not self.get("articles"):
            self.set("articles", [])
            for titre, corps in articles:
                self.append("articles", {"titre": titre, "corps": corps})

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


# ── API desk (bouton « Générer le corps par défaut ») ─────────────────────────
@frappe.whitelist()
def generer_corps_doc(name, force=1):
    """Depuis la fiche desk : (re)génère VU + préambule + articles fidèles au
    modèle à partir des éléments saisis, puis enregistre. `force=0` ne remplit que
    ce qui est vide (ne remplace pas les articles déjà édités)."""
    doc = frappe.get_doc("Avenant Contrat KYA", name)
    doc.check_permission("write")
    doc.generer_corps(force=int(force))
    doc.save()
    return {"articles": len(doc.articles or []), "workflow_state": doc.workflow_state}
