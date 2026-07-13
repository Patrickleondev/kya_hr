# -*- coding: utf-8 -*-
"""Logique serveur de calculs auto pour les DocTypes marqués `custom: 1`.

Sur ces DocTypes, Frappe ne charge PAS la classe controller Python — donc
les méthodes `validate()`, `before_submit()`, etc. définies dans le fichier
.py ne sont jamais appelées. Le code existant dans <doctype>.py est mort.

Pour pallier ça, on wrap les calculs nécessaires dans des fonctions
indépendantes, wirées via doc_events dans hooks.py.

DocTypes couverts (tous custom=1) :
- Demande Achat KYA : montant_total, palier
- Bon Commande KYA : sous_total, tva_montant, total_ttc + fournisseur_nom
- Tache Equipe : statut auto depuis taux_effectif
- Permission Sortie Stagiaire : nombre_jours, validation employee scope
"""
import frappe
from frappe.utils import flt, date_diff, today, get_fullname

from kya_hr.utils.approval_guards import block_self_approval


# ════════════════════════════════════════════════════════════════════
#  Demande Achat KYA
# ════════════════════════════════════════════════════════════════════

def compute_demande_achat(doc, method=None):
    """Recalcule montant_total + palier."""
    block_self_approval(doc)
    _set_employee_name(doc)
    _demande_achat_calculate_totals(doc)
    _demande_achat_set_palier(doc)


def _demande_achat_calculate_totals(doc):
    """Recalcule la somme des items.

    Si items renseignés avec prix → écrase montant_total.
    Sinon conserve la saisie manuelle.
    """
    items = doc.get("items") or []
    items_total = 0
    items_have_values = False
    for row in items:
        row.montant = (row.quantite or 0) * (row.prix_unitaire or 0)
        if row.montant:
            items_have_values = True
        items_total += row.montant

    if items_have_values:
        doc.montant_total = items_total
    elif not doc.montant_total:
        doc.montant_total = 0


def _demande_achat_set_palier(doc):
    m = doc.montant_total or 0
    urg = (doc.get("urgence") or "Normal").strip()
    urgent = urg in ("Urgent", "Très Urgent")
    if m > 15000000:
        base = "Palier 4 (> 15 000 000 XOF) — Appel d'offre international (60j) — Chef + DAAF + DG"
    elif m > 2000000:
        base = "Palier 3 (2 000 001 – 15 000 000 XOF) — Appel d'offre national (30j) — Chef + DAAF + DG"
    elif m > 100000:
        base = "Palier 2 (100 001 – 2 000 000 XOF) — 3 devis (1 sem.) — Chef + DAAF + DG"
    else:
        if urgent:
            base = "Palier 1 URGENT (≤ 100 000 XOF) — Validation DG requise (proc. accélérée)"
        else:
            base = "Palier 1 (≤ 100 000 XOF) — Procédure simplifiée (72h) — Chef + DAAF"
    if urgent:
        base += f" — 🚨 {urg}"
    doc.palier = base


# ════════════════════════════════════════════════════════════════════
#  Bon Commande KYA
# ════════════════════════════════════════════════════════════════════

def compute_bon_commande(doc, method=None):
    """Recalcule sous_total, tva_montant, total_ttc + fetch fournisseur_nom."""
    block_self_approval(doc)
    sous_total = 0.0
    for row in (doc.get("articles") or []):
        row.total = flt(row.quantite) * flt(row.prix_unitaire)
        sous_total += row.total
    doc.sous_total = sous_total
    base = sous_total - flt(doc.get("remise"))
    doc.tva_montant = base * flt(doc.get("tva_taux")) / 100.0
    doc.total_ttc = base + flt(doc.tva_montant)

    if doc.get("fournisseur") and not doc.get("fournisseur_nom"):
        doc.fournisseur_nom = frappe.db.get_value(
            "Supplier", doc.fournisseur, "supplier_name"
        )

    # Date d'autorisation : posée UNIQUEMENT au moment où une signature est
    # apposée (DG ou DGA), jamais avant. Si aucune signature -> pas de date.
    # (Demande métier : "que si le user signe, ça récupère la date courante".)
    if (doc.get("signature_dg") or doc.get("signature_dga")):
        if not doc.get("date_autorisation"):
            doc.date_autorisation = today()
    else:
        # Aucune signature : on ne laisse pas une date d'autorisation fantôme.
        doc.date_autorisation = None


# ════════════════════════════════════════════════════════════════════
#  Facture KYA
# ════════════════════════════════════════════════════════════════════

_FR_UNITS = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept",
             "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze",
             "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
_FR_TENS = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante",
            "soixante", "quatre-vingt", "quatre-vingt"]


def _fr_below_100(n):
    if n < 20:
        return _FR_UNITS[n]
    ten, unit = divmod(n, 10)
    if ten in (7, 9):                       # 70-79, 90-99 : base 60/80 + 10-19
        base = _FR_TENS[ten]
        return base + ("-" if base else "") + _FR_UNITS[10 + unit]
    word = _FR_TENS[ten]
    if unit == 0:
        # quatre-vingts prend un s ; vingt/... non
        return word + ("s" if ten == 8 else "")
    if unit == 1 and ten in (2, 3, 4, 5, 6):
        return word + " et un"
    return word + "-" + _FR_UNITS[unit]


def _fr_below_1000(n):
    if n < 100:
        return _fr_below_100(n)
    cent, rest = divmod(n, 100)
    if cent == 1:
        prefix = "cent"
    else:
        prefix = _FR_UNITS[cent] + " cent" + ("s" if rest == 0 else "")
    return prefix if rest == 0 else prefix + " " + _fr_below_100(rest)


def fr_number_in_words(n):
    """Entier positif -> mots français (jusqu'aux milliards). Ex. 4455326 ->
    'quatre millions quatre cent cinquante-cinq mille trois cent vingt-six'."""
    n = int(n)
    if n == 0:
        return "zéro"
    parts = []
    for value, singular, plural in ((10**9, "milliard", "milliards"),
                                    (10**6, "million", "millions"),
                                    (1000, "mille", "mille")):
        q, n = divmod(n, value)
        if q:
            if value == 1000 and q == 1:
                parts.append("mille")          # « mille » sans « un »
            else:
                word = _fr_below_1000(q)
                label = singular if q == 1 else plural
                # « mille » est invariable
                parts.append(word + " " + (label if value != 1000 else "mille"))
    if n:
        parts.append(_fr_below_1000(n))
    return " ".join(parts)


def compute_facture(doc, method=None):
    """Recalcule les totaux d'une Facture KYA (HT brut → remise % → TVA → TTC)
    + le montant en toutes lettres + le nom du client.

    Modèle métier (cf. FACTURE INFO) :
        total_ht_brut     = Σ (quantité × PU HT)
        remise_montant    = total_ht_brut × remise_taux / 100
        total_apres_remise= total_ht_brut − remise_montant
        tva_montant       = total_apres_remise × tva_taux / 100
        total_ttc         = total_apres_remise + tva_montant
    """
    block_self_approval(doc)
    total_ht_brut = 0.0
    for row in (doc.get("articles") or []):
        row.total = flt(row.quantite) * flt(row.prix_unitaire)
        total_ht_brut += row.total
    doc.total_ht_brut = total_ht_brut
    doc.remise_montant = total_ht_brut * flt(doc.get("remise_taux")) / 100.0
    doc.total_apres_remise = total_ht_brut - flt(doc.remise_montant)
    doc.tva_montant = flt(doc.total_apres_remise) * flt(doc.get("tva_taux")) / 100.0
    doc.total_ttc = flt(doc.total_apres_remise) + flt(doc.tva_montant)

    # Montant en toutes lettres (français, FCFA) — recalculé à chaque save.
    # money_in_words de Frappe est anglophone ; on produit le français au format
    # officiel « quatre millions … (4 455 326) francs CFA ».
    try:
        ttc = int(round(flt(doc.total_ttc)))
        lettres = fr_number_in_words(ttc)
        montant_fmt = "{:,.0f}".format(ttc).replace(",", " ")
        doc.montant_en_lettres = f"{lettres} ({montant_fmt}) francs CFA"
    except Exception:
        pass

    if doc.get("client") and not doc.get("client_nom"):
        doc.client_nom = frappe.db.get_value(
            "Customer", doc.client, "customer_name"
        )

    # Date d'établissement : posée quand une signature est apposée.
    if doc.get("signature"):
        if not doc.get("date_etablissement"):
            doc.date_etablissement = today()


# ════════════════════════════════════════════════════════════════════
#  Tache Equipe
# ════════════════════════════════════════════════════════════════════

def compute_tache_equipe(doc, method=None):
    """Met à jour le statut depuis taux_effectif."""
    taux = doc.get("taux_effectif") or 0
    if taux > 0:
        doc.statut = "Terminé" if taux >= 100 else "En cours"


# ════════════════════════════════════════════════════════════════════
#  Permission Sortie Stagiaire
# ════════════════════════════════════════════════════════════════════

def compute_permission_sortie_stagiaire(doc, method=None):
    """Validation scope + calcul nombre_jours."""
    block_self_approval(doc)
    _pss_validate_requester_scope(doc)
    _pss_validate_employee_is_intern(doc)
    _set_employee_name(doc)
    _pss_calc_nombre_jours(doc)


def _pss_can_select_any_employee(user=None):
    roles = set(frappe.get_roles(user or frappe.session.user))
    return bool({"System Manager", "HR Manager", "HR User", "Responsable RH"} & roles)


def _pss_current_active_employee(user=None):
    return frappe.db.get_value(
        "Employee",
        {"user_id": user or frappe.session.user, "status": "Active"},
        "name",
    )


def _pss_validate_requester_scope(doc):
    user = frappe.session.user
    # Ce périmètre ne concerne QUE la création par le demandeur (empêcher un
    # stagiaire de saisir pour un autre). Les approbateurs (maître de stage,
    # responsable des stagiaires, DG) ne font qu'avancer le workflow sur un
    # document existant : ils ne doivent PAS être re-scopés (sinon un maître de
    # stage non-RH est bloqué à l'approbation). Caught par les tests réalistes.
    if not doc.is_new() and user != doc.owner:
        return
    if user in ("Administrator", "Guest") or _pss_can_select_any_employee(user):
        return
    current_employee = _pss_current_active_employee(user)
    if not current_employee:
        frappe.throw("Aucun stagiaire actif n'est lié à votre compte utilisateur.")
    if not doc.get("employee"):
        doc.employee = current_employee
    elif doc.employee != current_employee:
        frappe.throw(
            "Vous ne pouvez pas créer une demande de permission pour un autre "
            "stagiaire. Le champ Stagiaire doit correspondre à votre compte connecté."
        )


def _pss_validate_employee_is_intern(doc):
    if doc.get("employee"):
        emp_type = frappe.db.get_value("Employee", doc.employee, "employment_type")
        if emp_type and emp_type != "Stage":
            frappe.throw(
                "Seuls les stagiaires peuvent utiliser ce formulaire. "
                "Les employés doivent utiliser le module Permission de Sortie Employé."
            )


def _pss_calc_nombre_jours(doc):
    if doc.get("date_fin") and doc.get("date_sortie"):
        diff = date_diff(doc.date_fin, doc.date_sortie)
        if diff < 0:
            frappe.throw("La date de fin ne peut pas être antérieure à la date de début.")
        doc.nombre_jours = diff + 1
    else:
        doc.nombre_jours = 1


# ════════════════════════════════════════════════════════════════════
#  Helper commun : Employee name auto-fetch
# ════════════════════════════════════════════════════════════════════

def _set_employee_name(doc):
    if doc.get("employee") and not doc.get("employee_name"):
        doc.employee_name = frappe.db.get_value(
            "Employee", doc.employee, "employee_name"
        )
