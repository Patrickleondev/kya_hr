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
from frappe import _
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


# ════════════════════════════════════════════════════════════════════
#  Bulletin Paie KYA  (moteur de paie lisant « Parametres Paie KYA »)
# ════════════════════════════════════════════════════════════════════

_MOIS_NUM = {
    "Janvier": "01", "Février": "02", "Mars": "03", "Avril": "04",
    "Mai": "05", "Juin": "06", "Juillet": "07", "Août": "08",
    "Septembre": "09", "Octobre": "10", "Novembre": "11", "Décembre": "12",
}


def _irpp_progressif(base, tranches):
    """Applique un barème progressif (liste de tranches min/max/taux) au revenu
    imposable mensuel `base`. L'impôt de chaque tranche ne porte que sur la
    fraction du revenu comprise dans la tranche."""
    impot = 0.0
    for t in tranches:
        tmin = flt(t.get("tranche_min"))
        tmax = flt(t.get("tranche_max"))
        taux = flt(t.get("taux"))
        if base <= tmin:
            continue
        borne_haute = base if (not tmax or tmax <= 0) else min(base, tmax)
        assiette = borne_haute - tmin
        if assiette > 0:
            impot += assiette * taux / 100.0
    return impot


def name_bulletin(doc, method=None):
    """Nomme le bulletin BP-<année>-<n°mois>-<matricule> (l'autoname du JSON
    référence mois_num, calculé seulement au validate qui court APRÈS le
    nommage → on force le nom ici)."""
    mn = _MOIS_NUM.get(doc.get("mois") or "", "00")
    doc.mois_num = mn
    doc.name = f"BP-{doc.get('annee')}-{mn}-{doc.get('employee')}"


def compute_bulletin(doc, method=None):
    """Calcule un Bulletin Paie KYA à partir des « Parametres Paie KYA ».

    Chaîne de calcul (toutes les valeurs de taux/barème viennent de la config
    saisie par le Comptable — aucune règle codée en dur) :
        brut_total      = salaire_base + Σ primes
        base_cnss       = (salaire_base + Σ primes soumises CNSS) plafonnée
        cnss_salarie    = base_cnss × taux CNSS salarié
        base_imposable  = (salaire_base + Σ primes imposables)
                          − abattement − CNSS (si déductible)
                          [− réduction charges si mode « base »]
        irpp            = barème progressif(base_imposable)
                          [− réduction charges si mode « impôt »]
        total_retenues  = cnss_salarie + irpp + autres_retenues
        net_a_payer     = brut_total − total_retenues
        cout_employeur  = brut_total + cnss_patronal
    """
    block_self_approval(doc)
    _set_employee_name(doc)

    # N° de mois + titre (sert à l'autoname et à l'affichage)
    doc.mois_num = _MOIS_NUM.get(doc.get("mois") or "", "00")
    if doc.get("employee_name"):
        doc.titre = f"{doc.employee_name} — {doc.get('mois')} {doc.get('annee')}"

    cfg = frappe.get_single("Parametres Paie KYA")

    base_sal = flt(doc.get("salaire_base"))

    # ── Gains ────────────────────────────────────────────────────────
    total_primes = 0.0
    primes_cnss = 0.0
    primes_imposables = 0.0
    for row in (doc.get("primes") or []):
        m = flt(row.get("montant"))
        total_primes += m
        if row.get("soumis_cnss"):
            primes_cnss += m
        if row.get("imposable"):
            primes_imposables += m
    doc.brut_total = base_sal + total_primes

    # ── CNSS (part salariale) ────────────────────────────────────────
    base_cnss = base_sal + primes_cnss
    plafond = flt(cfg.get("cnss_plafond"))
    if plafond > 0 and base_cnss > plafond:
        base_cnss = plafond
    doc.base_cnss = base_cnss
    doc.cnss_salarie = base_cnss * flt(cfg.get("cnss_taux_salarie")) / 100.0
    doc.cnss_patronal = base_cnss * flt(cfg.get("cnss_taux_patronal")) / 100.0

    # ── Abattement forfaitaire ───────────────────────────────────────
    brut_imposable = base_sal + primes_imposables
    abt = brut_imposable * flt(cfg.get("abattement_taux")) / 100.0
    abt_plafond = flt(cfg.get("abattement_plafond"))
    if abt_plafond > 0 and abt > abt_plafond:
        abt = abt_plafond
    doc.abattement_montant = abt

    # ── Réduction pour charges de famille ────────────────────────────
    nb = int(doc.get("nb_charges") or 0)
    nb_max = int(cfg.get("plafond_nb_charges") or 0)
    if nb_max > 0:
        nb = min(nb, nb_max)
    reduction = nb * flt(cfg.get("montant_par_charge"))
    mode_base = (cfg.get("charge_mode") == "Réduction de la base imposable")

    # ── Base imposable ───────────────────────────────────────────────
    base_imp = brut_imposable - abt
    if cfg.get("cnss_deductible_irpp"):
        base_imp -= flt(doc.cnss_salarie)
    if mode_base:
        base_imp -= reduction
    if base_imp < 0:
        base_imp = 0.0
    doc.base_imposable = base_imp

    # ── IRPP (barème progressif) ─────────────────────────────────────
    irpp = _irpp_progressif(base_imp, cfg.get("irpp_bareme") or [])
    if not mode_base:
        irpp -= reduction
    if irpp < 0:
        irpp = 0.0
    doc.irpp = irpp
    doc.reduction_charges = reduction

    # Le nombre de charges de famille est saisi bulletin par bulletin, mais son
    # effet dépend d'un paramètre GLOBAL. Si celui-ci vaut 0, la saisie n'a
    # aucune conséquence sur le net : sans alerte, le comptable croit accorder
    # une réduction qui n'est jamais appliquée.
    if nb > 0 and not flt(cfg.get("montant_par_charge")):
        frappe.msgprint(
            _("{0} charge(s) de famille sont saisies, mais le « Montant par charge » "
              "vaut 0 dans les Paramètres de Paie : aucune réduction n'est appliquée. "
              "Renseignez ce montant si la réduction pour charges de famille doit jouer.").format(nb),
            title=_("Réduction pour charges sans effet"), indicator="orange")

    # ── Retenues complémentaires ─────────────────────────────────────
    autres = 0.0
    for r in (cfg.get("retenues") or []):
        if not r.get("actif"):
            continue
        taux = flt(r.get("taux"))
        if taux:
            base_ret = doc.brut_total
            if r.get("base") == "Brut imposable":
                base_ret = brut_imposable
            elif r.get("base") == "Salaire de base":
                base_ret = base_sal
            autres += base_ret * taux / 100.0
        else:
            autres += flt(r.get("montant_fixe"))
    doc.autres_retenues = autres

    # ── Net & coût employeur ─────────────────────────────────────────
    doc.total_retenues = flt(doc.cnss_salarie) + flt(doc.irpp) + autres
    doc.net_a_payer = flt(doc.brut_total) - flt(doc.total_retenues)
    doc.cout_employeur = flt(doc.brut_total) + flt(doc.cnss_patronal)

    try:
        net = int(round(flt(doc.net_a_payer)))
        lettres = fr_number_in_words(net)
        montant_fmt = "{:,.0f}".format(net).replace(",", " ")
        doc.net_en_lettres = f"{lettres} ({montant_fmt}) francs CFA"
    except Exception:
        pass


@frappe.whitelist()
def prefill_primes_bulletin(bulletin_name=None):
    """Renvoie le catalogue de primes configuré, pour pré-remplir un bulletin
    côté client (bouton « Charger les primes du catalogue »)."""
    cfg = frappe.get_single("Parametres Paie KYA")
    out = []
    for p in (cfg.get("primes") or []):
        out.append({
            "libelle": p.get("libelle"),
            "montant": flt(p.get("montant_defaut")),
            "imposable": 1 if p.get("imposable") else 0,
            "soumis_cnss": 1 if p.get("soumis_cnss") else 0,
        })
    return out
