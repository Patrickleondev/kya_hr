# -*- coding: utf-8 -*-
"""Garantit l'en-tête KYA (logo + coordonnées) sur les PDF officiels.

Certains Print Formats maison n'avaient pas le bandeau KYA (logo + slogan +
coordonnées légales) : Demande Achat, PV Sortie, PV Entrée, Brouillard de Caisse,
Fiche Inventaire. Ce script ajoute un bandeau générique EN TÊTE du HTML, une seule
fois (marqueur anti-doublon). Non destructif : on ne touche qu'au début du HTML.

Idempotent. Rejoué à chaque migrate (les fixtures Print Format sont rechargées au
migrate ; on ré-applique le bandeau derrière).
"""
from __future__ import annotations

import frappe

MARQUEUR = "<!-- KYA-BRAND -->"

# Bandeau générique : logo à gauche, coordonnées à droite. Classes préfixées
# « kyab- » pour ne heurter aucun style existant du format.
BANDEAU = MARQUEUR + """
<style>
.kyab-head{display:flex;align-items:center;justify-content:space-between;
  border-bottom:2px solid #0E5C8A;padding-bottom:8px;margin-bottom:14px;
  font-family:Arial,Helvetica,sans-serif;}
.kyab-head .kyab-l img{max-height:58px;}
.kyab-head .kyab-r{text-align:right;font-size:9px;color:#555;line-height:1.4;}
.kyab-head .kyab-r .kyab-slog{color:#F77F00;font-weight:700;font-style:italic;
  font-size:11px;display:block;margin-bottom:2px;}
</style>
<div class="kyab-head">
  <div class="kyab-l">
    <img src="/assets/kya_hr/images/logo_kya.png" onerror="this.onerror=null;this.src='/files/vrai.png'">
  </div>
  <div class="kyab-r">
    <span class="kyab-slog">KYA, move beyond the sky!</span>
    info@kya-energy.com<br>
    N&deg; RCCM : TG-LOM 2015 B 975<br>
    NIF : 1000430317 &nbsp;|&nbsp; CNSS : 48863
  </div>
</div>
"""

# Print Formats à brander (ceux qui n'ont pas déjà le logo).
CIBLES = [
    "Demande Achat KYA Officiel",
    "PV Sortie Matériel Officiel",
    "Ticket Sortie Matériel",
    "Ticket Entrée Matériel KYA",
    "Brouillard Caisse KYA Officiel",
    "Fiche Inventaire KYA",
]


def execute() -> dict:
    out = {"brandes": [], "deja_ok": [], "absents": []}
    for name in CIBLES:
        if not frappe.db.exists("Print Format", name):
            out["absents"].append(name)
            continue
        html = frappe.db.get_value("Print Format", name, "html") or ""
        # Déjà branché (marqueur) OU déjà un logo KYA d'origine → on ne double pas.
        if MARQUEUR in html or "logo_kya" in html.lower():
            out["deja_ok"].append(name)
            continue
        frappe.db.set_value("Print Format", name, "html", BANDEAU + html,
                            update_modified=False)
        out["brandes"].append(name)
    frappe.clear_cache()
    frappe.db.commit()
    print(f"[ensure_pdf_branding] {out}")
    return out
