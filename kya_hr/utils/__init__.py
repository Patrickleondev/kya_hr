"""Utilitaires KYA HR.

Expose `get_kya_email_footer` et `nombre_en_lettres` (référencés par
hooks.py comme méthodes Jinja) et le module `approval_guards`.
"""
from __future__ import annotations


def get_kya_pangolin_note() -> str:
    """Rappel « code Pangolin » à glisser dans TOUT e-mail contenant un lien vers
    la plateforme. Le site est derrière un proxy SSO (Pangolin) : un lien ouvert
    hors session peut afficher un écran (souvent sombre) demandant un « code » à
    6 chiffres avant même la page de connexion KYA — sans ce rappel, un
    destinataire externe (garant, tuteur, établissement...) bloque dessus et
    abandonne. Un seul point d'insertion (ici + `get_kya_email_footer` /
    `kya_email_html`) pour que CHAQUE notification l'inclue automatiquement."""
    return (
        "<div style='background:#fff8e7;border-left:4px solid #e07b00;padding:12px 16px;"
        "margin:14px 0;font-size:13px;color:#333;font-family:Arial,Helvetica,sans-serif;'>"
        "🔒 <b>Aucun mot de passe supplémentaire à retenir.</b> Ouvrez simplement le lien avec "
        "votre compte KYA habituel (ou sans compte si le lien est personnel/à jeton). "
        "<b>Si une page (souvent sombre) vous demande un « code » à 6 chiffres</b>, tapez "
        "<b>1 1 1 1 1 1</b> (le chiffre 1, six fois) puis continuez."
        "</div>"
    )


def get_kya_email_footer() -> str:
    """Pied de page HTML standard pour les e-mails KYA-Energy Group.

    Utilisé dans les Email Templates via {{ get_kya_email_footer() }}.
    Table-based pour compatibilité Outlook (moteur Word). Inclut le rappel
    Pangolin (cf. `get_kya_pangolin_note`) pour que tout e-mail qui l'utilise en
    bénéficie automatiquement, sans avoir à retoucher chaque notification.
    """
    return (
        get_kya_pangolin_note() +
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin-top:18px;border-top:1px solid #e0e0e0;font-family:Arial,Helvetica,sans-serif;">'
        '<tr><td style="padding-top:12px;font-size:12px;color:#666666;line-height:1.5;">'
        '<strong style="color:#00897B;">KYA-Energy Group</strong> — Move beyond the sky!<br/>'
        "Cet e-mail est généré automatiquement par le système KYA. "
        "Merci de ne pas y répondre directement."
        "</td></tr></table>"
    )


def kya_email_html(title: str, body_html: str, subtitle: str = "",
                   accent: str = "#e07b00", footer: bool = True) -> str:
    """Gabarit e-mail KYA **compatible Outlook** (moteur Word).

    Règles Outlook respectées : mise en page 100 % en <table>, largeur fixe
    600px, styles INLINE, en-tête en couleur PLEINE via attribut bgcolor (pas
    de linear-gradient — Outlook l'ignore et afficherait un bandeau blanc),
    polices Arial, pas de flex / border-radius / max-width comme seul recours.

    `title`  : titre du bandeau.   `subtitle` : ligne secondaire (optionnel).
    `body_html` : contenu HTML déjà formaté (paragraphes, listes...).
    `accent` : couleur pleine du bandeau (orange KYA par défaut).
    """
    sub = (
        '<br/><span style="font-size:13px;color:#ffffff;opacity:0.95;">%s</span>' % subtitle
        if subtitle else ""
    )
    foot = (
        ('<tr><td style="padding:14px 28px 0;">' + get_kya_pangolin_note() + '</td></tr>')
        + '<tr><td style="padding:14px 28px;border-top:1px solid #e0e0e0;color:#888888;'
        'font-size:12px;line-height:1.5;font-family:Arial,Helvetica,sans-serif;">'
        '<strong style="color:#00897B;">KYA-Energy Group</strong> — LOMÉ, TOGO — '
        'Move beyond the sky!<br/>E-mail automatique, merci de ne pas y répondre.'
        '</td></tr>'
        if footer else ""
    )
    return (
        '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" '
        'style="background:#f4f4f4;padding:0;margin:0;"><tr>'
        '<td align="center" style="padding:16px;">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="width:600px;max-width:600px;background:#ffffff;border:1px solid #e0e0e0;'
        'font-family:Arial,Helvetica,sans-serif;">'
        # En-tête couleur pleine (bgcolor + style pour Outlook ET clients modernes)
        '<tr><td bgcolor="%s" style="background:%s;padding:22px 28px;font-family:Arial,Helvetica,sans-serif;">'
        '<span style="font-size:20px;font-weight:bold;color:#ffffff;">%s</span>%s'
        '</td></tr>'
        # Corps
        '<tr><td style="padding:24px 28px;color:#333333;font-size:14px;line-height:1.6;'
        'font-family:Arial,Helvetica,sans-serif;">%s</td></tr>'
        '%s'
        '</table></td></tr></table>'
        % (accent, accent, title, sub, body_html, foot)
    )


# ─── Nombre en lettres françaises (contrats : "350 000" -> "trois cent cinquante mille") ───

_UNITS_FR = [
    "", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
    "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize",
    "dix-sept", "dix-huit", "dix-neuf",
]
_TENS_FR = [
    "", "", "vingt", "trente", "quarante", "cinquante", "soixante",
    "soixante", "quatre-vingt", "quatre-vingt",
]


def _below_hundred(n: int, plural_ok: bool = True) -> str:
    """`plural_ok=False` désactive le `s` de `quatre-vingts` (avant mille/million)."""
    if n < 20:
        return _UNITS_FR[n]
    tens, units = divmod(n, 10)
    if tens in (7, 9):
        base = _TENS_FR[tens]
        rest = _UNITS_FR[10 + units]
        return f"{base}-{rest}" if units else f"{base}-dix"
    base = _TENS_FR[tens]
    if units == 0:
        return base + ("s" if tens == 8 and plural_ok else "")
    if units == 1 and tens in (2, 3, 4, 5, 6):
        return f"{base} et un"
    return f"{base}-{_UNITS_FR[units]}"


def _below_thousand(n: int, plural_ok: bool = True) -> str:
    """`plural_ok=False` désactive le `s` de `cents` (avant mille/million)."""
    if n < 100:
        return _below_hundred(n, plural_ok=plural_ok)
    hundreds, rest = divmod(n, 100)
    if hundreds == 1:
        prefix = "cent"
    else:
        prefix = f"{_UNITS_FR[hundreds]} cent" + ("s" if rest == 0 and plural_ok else "")
    if rest == 0:
        return prefix
    return f"{prefix} {_below_hundred(rest)}"


_MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre",
    12: "décembre",
}


def date_fr(d) -> str:
    """« 01 juillet 2026 » — date en français, INDÉPENDANTE de la locale/contexte
    d'impression (frappe.utils.formatdate rend « July » hors print_language('fr'))."""
    if not d:
        return ""
    try:
        from frappe.utils import getdate
        dt = getdate(d)
    except Exception:
        return ""
    return "%02d %s %d" % (dt.day, _MOIS_FR.get(dt.month, ""), dt.year)


def nombre_en_lettres(n, devise: str = "francs CFA") -> str:
    """Convertit un nombre entier en lettres françaises (Togo / FCFA).

    Exemples:
      nombre_en_lettres(28000) -> "vingt-huit mille francs CFA"
      nombre_en_lettres(350000) -> "trois cent cinquante mille francs CFA"
      nombre_en_lettres(1500000) -> "un million cinq cent mille francs CFA"

    Si `devise` est None ou vide, retourne juste les lettres sans suffixe.
    """
    if n is None:
        return ""
    try:
        n = int(round(float(n)))
    except (TypeError, ValueError):
        return ""
    if n < 0:
        return "moins " + nombre_en_lettres(-n, devise)
    if n == 0:
        result = "zéro"
    else:
        parts = []
        millions, rest = divmod(n, 1_000_000)
        thousands, units = divmod(rest, 1_000)
        if millions:
            if millions == 1:
                parts.append("un million")
            else:
                # plural_ok=True ici car "deux cents millions" est correct
                parts.append(f"{_below_thousand(millions)} millions")
        if thousands:
            if thousands == 1:
                parts.append("mille")
            else:
                # plural_ok=False : "cinq cent mille" (pas "cinq cents mille")
                parts.append(f"{_below_thousand(thousands, plural_ok=False)} mille")
        if units:
            parts.append(_below_thousand(units))
        result = " ".join(parts)
    if devise:
        return f"{result} {devise}"
    return result
