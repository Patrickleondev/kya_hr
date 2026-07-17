# -*- coding: utf-8 -*-
"""KYA Contract Template — constructeur de modèles de contrat pour la RH.

La RH compose un contrat article par article (table `articles`), en texte
libre, avec deux mécanismes SIMPLES (pas de Jinja, pas de code) :

  • Variables entre accolades :  {employe} {civilite} {civilite_longue} {poste}
    {type_contrat} {date_debut} {date_fin} {date_jour} {entreprise} {dg}
    ({civilite} = M./Mme/Mlle ; {civilite_longue} = Monsieur/Madame/Mademoiselle)
  • Accord masculin/féminin avec une barre :  {Le|La}  embauché{|e}  {il|elle}
    (avant la barre = masculin, après = féminin ; selon le Sexe du contrat)

`render_for(ctx_doc)` produit le HTML final à partir d'un document KYA Contrat.
Si la table `articles` est vide, on retombe sur `html_body` (mode avancé Jinja).
"""
import re

import frappe
from frappe.model.document import Document
from frappe.utils import formatdate, today, getdate

# Mois en français : formatdate("dd MMMM yyyy") dépend de la locale du serveur
# et rend souvent l'anglais ("22 May 2026"). On force le français.
_MOIS_FR = ["", "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _date_fr(value):
    """Retourne 'j mois aaaa' en français, ou '' si vide."""
    if not value:
        return ""
    g = getdate(value)
    return f"{g.day} {_MOIS_FR[g.month]} {g.year}"


# Réécrit les appels Jinja `formatdate(<expr>, 'dd MMMM yyyy')` des html_body en
# `date_fr(<expr>)` (les modèles CDI/CDD embarquent ce format anglais en dur).
_FORMATDATE_FR_RE = re.compile(
    r"frappe\.utils\.formatdate\(\s*(.+?)\s*,\s*['\"]dd MMMM yyyy['\"]\s*\)"
)


# {masculin|féminin} — la barre distingue les deux formes.
_GENDER_RE = re.compile(r"\{([^{}|]*)\|([^{}]*)\}")
# {variable} — sans barre.
_VAR_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class KYAContractTemplate(Document):
    def validate(self):
        if self.is_active:
            # Un seul template actif par (type de contrat, genre visé).
            # Le genre DOIT entrer dans la clé : sans lui, installer
            # « CDD — Masculin » éteignait « CDD — Féminin », et toutes les
            # femmes recevaient un contrat au masculin (« Monsieur <nom> »).
            frappe.db.sql(
                """UPDATE `tabKYA Contract Template`
                   SET is_active = 0
                   WHERE contract_type = %s AND genre_cible = %s AND name != %s""",
                (self.contract_type, self.genre_cible, self.name),
            )

    # ── Rendu ────────────────────────────────────────────────────────────
    def render_for(self, ctx_doc):
        """Retourne le HTML du corps du contrat pour un KYA Contrat donné."""
        ctx = _build_context(ctx_doc)
        is_masc = ctx["_is_masc"]
        if self.get("articles"):
            blocks = []
            for art in self.articles:
                titre = (art.numero or "").strip()
                if art.titre:
                    titre = (titre + " : " + art.titre) if titre else art.titre
                contenu = _substitute(art.contenu or "", ctx, is_masc)
                head = (
                    '<h3 class="art">%s</h3>' % frappe.utils.escape_html(titre)
                    if titre else ""
                )
                blocks.append('<div class="kya-article">%s%s</div>' % (head, contenu))
            return "\n".join(blocks)
        # Repli : mode avancé html_body (Jinja)
        if self.html_body:
            try:
                body = _FORMATDATE_FR_RE.sub(r"date_fr(\1)", self.html_body)
                return frappe.render_template(
                    body, {"doc": ctx_doc, "frappe": frappe, "date_fr": _date_fr}
                )
            except Exception:
                return self.html_body
        return ""

    @frappe.whitelist()
    def get_preview(self):
        """Aperçu RH : rend les articles avec un contrat fictif (genre = genre_cible)."""
        sample = frappe._dict({
            "employee_name": "NOM Prénom",
            "sexe": "Féminin" if self.genre_cible == "Féminin" else "Masculin",
            "poste": "Intitulé du poste",
            "contract_type": self.contract_type,
            "date_debut": today(),
            "date_fin": today(),
        })
        return self.render_for(sample)


# Situations de famille impliquant « Madame » (femme non célibataire).
_SITUATIONS_MADAME = ("Marié(e)", "Divorcé(e)", "Veuf/Veuve", "Union libre")


def compute_civilite(sexe, situation=None):
    """Civilité française à partir du sexe et de la situation de famille.

    - Masculin                       → « Monsieur »
    - Féminin + mariée/veuve/div/UL  → « Madame »
    - Féminin + célibataire (ou inconnu) → « Mademoiselle »

    Sert de valeur PAR DÉFAUT : la RH peut toujours forcer une autre civilité
    sur le contrat (une dame célibataire à qui on veut dire « Madame »)."""
    if str(sexe or "").lower().startswith("m"):
        return "Monsieur"
    if situation in _SITUATIONS_MADAME:
        return "Madame"
    return "Mademoiselle"


# Forme abrégée pour l'en-tête de contrat (M. / Mme / Mlle).
_CIVILITE_ABR = {"Monsieur": "M.", "Madame": "Mme", "Mademoiselle": "Mlle"}


def _build_context(ctx_doc):
    """Construit le dictionnaire de variables conviviales depuis un KYA Contrat."""
    def g(field):
        if hasattr(ctx_doc, "get"):
            return ctx_doc.get(field)
        return getattr(ctx_doc, field, None)

    sexe = g("sexe") or "Masculin"
    is_masc = str(sexe).lower().startswith("m")
    # Civilité : valeur saisie/corrigée par la RH en priorité, sinon calculée
    # depuis sexe + situation de famille (contrats antérieurs au champ civilite).
    civilite_longue = g("civilite") or compute_civilite(sexe, g("situation_famille"))
    return {
        "employe": g("employee_name") or "",
        "civilite": _CIVILITE_ABR.get(civilite_longue, "M." if is_masc else "Mme"),
        "civilite_longue": civilite_longue,
        "poste": g("poste") or "",
        "type_contrat": g("contract_type") or "",
        "date_debut": _date_fr(g("date_debut")),
        "date_fin": _date_fr(g("date_fin")),
        "date_jour": _date_fr(today()),
        "entreprise": "KYA-Energy Group",
        "dg": g("nom_dg") or "Prof. Yao AZOUMAH",
        "_is_masc": is_masc,
    }


def _substitute(text, ctx, is_masc):
    """Résout d'abord les accords {m|f}, puis les variables {nom}."""
    if not text:
        return ""

    def gender_sub(m):
        return m.group(1) if is_masc else m.group(2)

    text = _GENDER_RE.sub(gender_sub, text)

    def var_sub(m):
        key = m.group(1)
        if key in ctx:
            return frappe.utils.escape_html(str(ctx[key]))
        return m.group(0)  # variable inconnue : laissée telle quelle (typo visible)

    return _VAR_RE.sub(var_sub, text)
