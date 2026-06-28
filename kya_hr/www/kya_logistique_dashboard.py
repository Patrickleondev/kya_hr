"""Page Dashboard Logistique. Route : /kya-logistique-dashboard."""
from __future__ import annotations

import frappe


ACCESS_ROLES = {
    "System Manager", "Directeur General", "Directeur Général", "DG", "DGA",
    "Responsable Logistique", "Logisticien", "Chef Service",
    "Chef Service Achats", "Auditeur",
    # Gestion de flotte + RH (la RH tient la logistique sur tablette)
    "Gestionnaire de Flotte", "Fleet Manager",
    "Responsable RH", "HR Manager",
}


def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/kya-logistique-dashboard"
        raise frappe.Redirect

    user_roles = set(frappe.get_roles(user))
    if not (user_roles & ACCESS_ROLES):
        frappe.throw(
            "Acces refuse - role Logistique requis (Logisticien, "
            "DG, DGA, ou Auditeur).",
            frappe.PermissionError,
        )

    context.page_title = "Dashboard Logistique KYA"
    context.no_cache = 1
    context.no_breadcrumbs = True
    try:
        import json as _json
        context.overview_json = _json.dumps(get_logistique_overview(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "logistique-dashboard: overview")
    return context


# ════════════════════════════════════════════════════════════════════
#  Vue d'ensemble Logistique & Flotte (maquette boards/Dashboard
#  Logistique) — données réelles
# ════════════════════════════════════════════════════════════════════
def _exists(dt):
    try:
        return bool(frappe.db.exists("DocType", dt))
    except Exception:
        return False


def _count(dt, filters=None):
    if not _exists(dt):
        return 0
    try:
        return frappe.db.count(dt, filters or {})
    except Exception:
        return 0


@frappe.whitelist()
def get_logistique_overview() -> dict:
    """Indicateurs Logistique & Flotte (véhicules, sorties, carburant,
    entretiens, kilométrage). Réel et défensif."""
    if not (set(frappe.get_roles(frappe.session.user)) & ACCESS_ROLES):
        frappe.throw("Accès réservé à la logistique et à la Direction.", frappe.PermissionError)

    from frappe.utils import flt, today, add_days, get_first_day, formatdate, get_datetime

    month_start = str(get_first_day(today()))
    six_m = str(add_days(today(), -185))

    # ── Flotte ──
    vehicles = []
    if _exists("Vehicle"):
        try:
            vehicles = frappe.get_all("Vehicle",
                fields=["name", "license_plate", "make", "model", "kya_statut"],
                limit_page_length=500)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "logi-overview: vehicles")
    total_v = len(vehicles)
    dispo = sum(1 for v in vehicles if (v.kya_statut or "") == "Disponible")
    en_mission_v = sum(1 for v in vehicles if (v.kya_statut or "") == "En mission")
    en_entretien_v = sum(1 for v in vehicles if (v.kya_statut or "") == "En entretien")

    # ── Sorties véhicule ──
    sorties = []
    if _exists("Sortie Vehicule"):
        try:
            sorties = frappe.get_all("Sortie Vehicule",
                fields=["name", "license_plate", "vehicle_make_model", "chauffeur_name",
                        "motif_mission", "destination", "date_depart", "date_retour_prevue",
                        "km_parcourus", "statut"],
                order_by="date_depart desc", limit_page_length=500)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "logi-overview: sorties")
    en_cours = [s for s in sorties if (s.statut or "") in ("Approuvée", "En mission")]
    sorties_jour = sum(1 for s in sorties if str(s.date_depart or "")[:10] == today())

    # ── Carburant ──
    pleins = []
    if _exists("Plein Carburant KYA"):
        try:
            pleins = frappe.get_all("Plein Carburant KYA",
                fields=["license_plate", "date_plein", "litres", "montant"],
                order_by="date_plein desc", limit_page_length=1000)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "logi-overview: pleins")
    litres_mois = sum(flt(p.litres) for p in pleins if str(p.date_plein or "") >= month_start)
    montant_mois = sum(flt(p.montant) for p in pleins if str(p.date_plein or "") >= month_start)

    # ── Entretiens ──
    entretiens = []
    if _exists("Entretien Vehicule KYA"):
        try:
            entretiens = frappe.get_all("Entretien Vehicule KYA",
                fields=["license_plate", "vehicle_make_model", "type_entretien", "statut",
                        "date_entretien", "prochaine_echeance_date", "km_actuel",
                        "prochaine_echeance_km"],
                order_by="prochaine_echeance_date asc, date_entretien desc",
                limit_page_length=500)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "logi-overview: entretiens")
    a_prevoir = [e for e in entretiens if (e.statut or "") in ("Planifié", "En cours")]

    taux = round((en_mission_v / total_v) * 100) if total_v else 0

    def _hm(dt):
        if not dt:
            return "—"
        try:
            return get_datetime(dt).strftime("%d/%m %H:%M")
        except Exception:
            return str(dt)[:16]

    # ── Hero (6) ──
    montant_m = (montant_mois or 0) / 1_000_000.0
    hero = [
        {"label": "Véhicules disponibles", "value": str(dispo), "unit": f"/ {total_v}",
         "sub": "flotte au dépôt", "icon": "truck"},
        {"label": "En mission", "value": str(en_mission_v or len(en_cours)), "sub": "sur le terrain", "icon": "route"},
        {"label": "Sorties du jour", "value": str(sorties_jour), "sub": "départs enregistrés", "icon": "calendar"},
        {"label": "Carburant (mois)", "value": f"{litres_mois:,.0f}".replace(",", " "), "unit": "L",
         "sub": (f"≈ {montant_m:,.1f} M FCFA".replace(",", " ").replace(".", ",") if montant_mois else "ce mois"), "icon": "fuel"},
        {"label": "Entretiens à prévoir", "value": str(len(a_prevoir)), "sub": "planifiés / en cours", "icon": "wrench"},
        {"label": "Taux d'utilisation", "value": str(taux), "unit": "%", "sub": "flotte en mission", "icon": "gauge"},
    ]

    # ── Sorties en cours (table) ──
    st_badge = {"En mission": "wait", "Approuvée": "teal", "Retour confirmé": "ok",
                "Brouillon": "slate", "Annulée": "bad"}
    sortie_rows = []
    for s in en_cours[:8]:
        sortie_rows.append({
            "vehicule": s.license_plate or s.vehicle_make_model or "—",
            "conducteur": s.chauffeur_name or "—",
            "motif": s.motif_mission or s.destination or "—",
            "depart": _hm(s.date_depart), "retour": _hm(s.date_retour_prevue),
            "statut": s.statut or "—", "accent": st_badge.get(s.statut or "", "teal"),
        })

    # ── Entretiens planifiés (table) ──
    ent_badge = {"Planifié": "wait", "En cours": "warn", "Terminé": "ok"}
    entretien_rows = []
    for e in a_prevoir[:8]:
        km = e.prochaine_echeance_km or e.km_actuel or 0
        entretien_rows.append({
            "vehicule": e.license_plate or e.vehicle_make_model or "—",
            "type": e.type_entretien or "—",
            "echeance": formatdate(e.prochaine_echeance_date, "dd/MM/y") if e.prochaine_echeance_date else (formatdate(e.date_entretien, "dd/MM/y") if e.date_entretien else "—"),
            "km": (f"{int(km):,}".replace(",", " ") + " km") if km else "—",
            "statut": e.statut or "—", "accent": ent_badge.get(e.statut or "", "wait"),
        })

    # ── Carburant par mois (6 mois, L) ──
    fuel = {"labels": [], "data": []}
    by_month = {}
    for p in pleins:
        d = str(p.date_plein or "")
        if not d or d < six_m:
            continue
        by_month[d[:7]] = by_month.get(d[:7], 0.0) + flt(p.litres)
    for k in sorted(by_month):
        fuel["labels"].append(k)
        fuel["data"].append(round(by_month[k]))

    # ── Kilométrage par véhicule (6 mois) ──
    by_veh = {}
    for s in sorties:
        d = str(s.date_depart or "")
        if not d or d[:10] < six_m:
            continue
        key = s.license_plate or s.vehicle_make_model or "—"
        by_veh[key] = by_veh.get(key, 0) + int(flt(s.km_parcourus))
    veh_sorted = sorted(by_veh.items(), key=lambda kv: kv[1], reverse=True)[:8]
    util = {"labels": [k for k, _v in veh_sorted], "data": [v for _k, v in veh_sorted]}

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero, "sortie_rows": sortie_rows, "entretien_rows": entretien_rows,
        "fuel": fuel, "util": util,
        "en_mission_label": f"{en_mission_v or len(en_cours)} en mission",
        "a_prevoir_label": f"{len(a_prevoir)} à prévoir",
    }
