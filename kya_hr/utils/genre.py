# -*- coding: utf-8 -*-
"""Moteur d'accords en genre (français) — civilité dynamique et accords.

Utilisé par tous les documents RH (certificats, attestations, avenants, contrats
de stage) pour que le rendu soit grammaticalement juste selon le genre de la
personne : « né(e) », « dénommé(e) », « désigné(e) », « L'Employé(e) », etc.

On part du genre ERPNext ("Male"/"Female") OU d'une civilité explicite
(M. / Mme / Mlle), la civilité primant si fournie (l'agent RH sait, par ex.,
qu'une personne est « Mlle »).
"""

_FEMS_CIV = {"mme", "mme.", "madame", "mlle", "mlle.", "mademoiselle"}
_MASC_CIV = {"m.", "m", "mr", "mr.", "monsieur"}


def est_feminin(gender=None, civilite=None):
    """Vrai si le genre à retenir est féminin. La civilité prime sur le genre."""
    if civilite:
        c = str(civilite).strip().lower()
        if c in _FEMS_CIV:
            return True
        if c in _MASC_CIV:
            return False
    return str(gender or "").strip().lower() in ("female", "féminin", "feminin", "f")


def civilite_defaut(gender=None, civilite=None):
    """Civilité à afficher : respecte une civilité explicite, sinon déduit du genre."""
    if civilite and str(civilite).strip():
        return str(civilite).strip()
    return "Mme" if est_feminin(gender) else "M."


def accords(gender=None, civilite=None):
    """Renvoie un dict de tous les accords en genre prêts pour les gabarits.

    Chaque clé existe en variante minuscule et Capitale quand c'est utile.
    """
    f = est_feminin(gender, civilite)

    def g(masc, fem):
        return fem if f else masc

    return {
        "feminin": f,
        "civilite": civilite_defaut(gender, civilite),
        # articles / pronoms
        "le_la": g("le", "la"),
        "Le_La": g("Le", "La"),
        "il_elle": g("il", "elle"),
        "Il_Elle": g("Il", "Elle"),
        "du_dela": g("du", "de la"),
        "au_ala": g("au", "à la"),
        # accords fréquents (participe passé / adjectifs)
        "ne": g("né", "née"),
        "denomme": g("dénommé", "dénommée"),
        "designe": g("désigné", "désignée"),
        "couvert": g("couvert", "couverte"),
        "soumis": g("soumis", "soumise"),
        "evalue": g("évalué", "évaluée"),
        "domicilie": g("domicilié", "domiciliée"),
        "interesse": g("intéressé", "intéressée"),
        "promu": g("promu", "promue"),
        "employe": g("Employé", "Employée"),
        "employe_min": g("employé", "employée"),
        "fils_fille": g("Fils", "Fille"),
        "titulaire": g("titulaire", "titulaire"),
        # fonctions genrées courantes (best effort ; l'agent RH peut écraser)
        "chef_cheffe": g("Chef", "Cheffe"),
    }


def resoudre_from_employee(employee):
    """Accords à partir d'une fiche Employee (genre + civilité éventuelle)."""
    import frappe
    if not employee:
        return accords()
    gender = frappe.db.get_value("Employee", employee, "gender")
    return accords(gender=gender)
