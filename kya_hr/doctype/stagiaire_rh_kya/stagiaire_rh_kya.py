"""Registre RH des stagiaires (feuille « Stagiaires » du classeur RH) —
hors effectif salarié. Durée et statut calculés automatiquement, comme
dans le classeur."""
import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, getdate, today


def duree_lisible(debut, fin):
    """« X mois » / « X jour(s) » entre deux dates (fin exclue si absente)."""
    if not debut or not fin:
        return ""
    jours = date_diff(fin, debut)
    if jours < 0:
        return ""
    if jours >= 30:
        mois = round(jours / 30.44, 1)
        mois = int(mois) if mois == int(mois) else mois
        return "%s mois" % mois
    return "%d jour(s)" % jours


def statut_periode(debut, fin):
    """À venir / En cours / Terminé selon les dates (comme le classeur)."""
    auj = getdate(today())
    if debut and getdate(debut) > auj:
        return "À venir"
    if fin and getdate(fin) < auj:
        return "Terminé"
    if debut:
        return "En cours"
    return ""


class StagiaireRHKYA(Document):
    def validate(self):
        self.nom_complet = " ".join(x for x in [(self.nom or "").strip().upper(),
                                                (self.prenoms or "").strip()] if x)
        self.duree = duree_lisible(self.date_debut, self.date_fin)
        self.statut = statut_periode(self.date_debut, self.date_fin)
