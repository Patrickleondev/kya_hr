"""Utilitaires KYA HR.

Expose `get_kya_email_footer` et `nombre_en_lettres` (référencés par
hooks.py comme méthodes Jinja) et le module `approval_guards`.
"""
from __future__ import annotations


def get_kya_email_footer() -> str:
    """Pied de page HTML standard pour les e-mails KYA-Energy Group.

    Utilisé dans les Email Templates via {{ get_kya_email_footer() }}.
    """
    return (
        '<div style="margin-top:24px;padding-top:12px;border-top:1px solid #e0e0e0;'
        'font-size:12px;color:#666;font-family:Arial,sans-serif;line-height:1.5;">'
        '<strong style="color:#00897B;">KYA-Energy Group</strong><br/>'
        "Cet e-mail est généré automatiquement par le système KYA. "
        "Merci de ne pas y répondre directement."
        "</div>"
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
