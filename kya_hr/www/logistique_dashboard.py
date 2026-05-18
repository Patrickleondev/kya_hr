"""Dashboard Logistique — flotte de véhicules KYA uniquement.

Centré sur :
- Vehicle (ERPNext) : véhicules + assurance + conducteur
- Document Vehicule (KYA) : carte grise, vignette, visite, etc. + alertes expiration
- Vehicle Log (ERPNext) : km parcourus + consommation carburant + entretien

Accessible : Fleet Manager, Gestionnaire de Flotte, Responsable Logistique,
DAAF, DGA, DG, System Manager.
"""
import frappe
from frappe.utils import add_days, flt, today, cint, getdate


no_cache = 1


_ALLOWED_ROLES = {
    "System Manager", "Administrator",
    "Fleet Manager", "Gestionnaire de Flotte",
    "DST - Responsable Logistique", "Responsable Logistique",
    "DAAF", "DGA", "Directeur Général", "DG",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/logistique-dashboard"
        raise frappe.Redirect

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not (_ALLOWED_ROLES & user_roles):
        frappe.throw("Accès réservé à la gestion de flotte / direction.", frappe.PermissionError)

    period = cint(frappe.form_dict.get("period") or 30)

    context.title = "Dashboard Logistique — Flotte"
    context.no_breadcrumbs = True
    context.period = period
    context.today_label = today()

    # ─── KPIs FLOTTE GLOBALE ─────────────────────────────────────────────
    context.flotte = _flotte_kpis()

    # ─── DOCUMENTS (carte grise / assurance / visite / vignette) ────────
    context.documents = _documents_kpis(period)

    # ─── VEHICULES par etat (assurance, expiration) ──────────────────────
    context.vehicules = _vehicules_list()

    # ─── ALERTES (top 10 documents urgents a renouveler) ────────────────
    context.alertes = _alertes_urgentes()

    # ─── REPARTITION (marque / carburant / conducteur) ──────────────────
    context.repartition = _repartition()

    # ─── KILOMETRAGE + ENTRETIEN (Vehicle Log si dispo) ─────────────────
    context.activite = _activite_vehicles(period)


def _flotte_kpis():
    """KPIs globaux : nombre, valeur, conducteurs."""
    if not frappe.db.exists("DocType", "Vehicle"):
        return {"total": 0, "valeur_totale": 0, "avec_conducteur": 0, "sans_conducteur": 0}
    rows = frappe.get_all(
        "Vehicle",
        fields=["name", "license_plate", "vehicle_value", "employee", "end_date"],
        limit_page_length=0,
    )
    total = len(rows)
    valeur = sum(flt(r.vehicle_value or 0) for r in rows)
    avec_cond = sum(1 for r in rows if r.employee)
    today_d = getdate()
    assurance_expiree = sum(1 for r in rows if r.end_date and getdate(r.end_date) < today_d)
    assurance_30j = sum(
        1 for r in rows
        if r.end_date and 0 <= (getdate(r.end_date) - today_d).days <= 30
    )
    return {
        "total": total,
        "valeur_totale": round(valeur, 0),
        "avec_conducteur": avec_cond,
        "sans_conducteur": total - avec_cond,
        "assurance_expiree": assurance_expiree,
        "assurance_30j": assurance_30j,
    }


def _documents_kpis(period):
    """Stats Document Vehicule : expirations, coûts."""
    if not frappe.db.exists("DocType", "Document Vehicule"):
        return {"total": 0, "expires": 0, "expire_30j": 0, "expire_60j": 0, "cout_total": 0, "par_type": {}}

    today_d = getdate()
    rows = frappe.get_all(
        "Document Vehicule",
        fields=["name", "vehicle", "type_document", "date_expiration", "cout_xof"],
        limit_page_length=0,
    )
    total = len(rows)
    expires = 0
    expire_30j = 0
    expire_60j = 0
    cout_total = 0
    par_type = {}
    for r in rows:
        cout_total += flt(r.cout_xof or 0)
        t = r.type_document or "Non défini"
        par_type[t] = par_type.get(t, 0) + 1
        if not r.date_expiration:
            continue
        delta = (getdate(r.date_expiration) - today_d).days
        if delta < 0:
            expires += 1
        elif delta <= 30:
            expire_30j += 1
        elif delta <= 60:
            expire_60j += 1
    return {
        "total": total,
        "expires": expires,
        "expire_30j": expire_30j,
        "expire_60j": expire_60j,
        "cout_total": round(cout_total, 0),
        "par_type": par_type,
    }


def _vehicules_list():
    """Liste détaillée des véhicules avec leur état."""
    if not frappe.db.exists("DocType", "Vehicle"):
        return []
    rows = frappe.get_all(
        "Vehicle",
        fields=["name", "license_plate", "make", "model", "vehicle_value",
                "employee", "last_odometer", "end_date", "fuel_type", "carbon_check_date"],
        order_by="license_plate asc",
        limit_page_length=50,
    )
    today_d = getdate()
    for r in rows:
        r["conducteur_name"] = ""
        if r.employee:
            r["conducteur_name"] = frappe.db.get_value("Employee", r.employee, "employee_name") or r.employee
        # État assurance
        if r.end_date:
            delta = (getdate(r.end_date) - today_d).days
            if delta < 0:
                r["assurance_etat"] = "expired"
                r["assurance_label"] = f"Expirée depuis {-delta}j"
            elif delta <= 30:
                r["assurance_etat"] = "warning"
                r["assurance_label"] = f"Expire dans {delta}j"
            else:
                r["assurance_etat"] = "ok"
                r["assurance_label"] = f"OK ({delta}j restants)"
        else:
            r["assurance_etat"] = "missing"
            r["assurance_label"] = "Non renseignée"
    return rows


def _alertes_urgentes():
    """Top 10 documents véhicule urgents à renouveler (expirés ou < 30j)."""
    if not frappe.db.exists("DocType", "Document Vehicule"):
        return []
    today_d = getdate()
    in_30j = add_days(today_d, 30)
    rows = frappe.db.sql(
        """
        SELECT dv.name, dv.vehicle, dv.type_document, dv.numero,
               dv.date_expiration, dv.cout_xof, v.license_plate, v.make, v.model
        FROM `tabDocument Vehicule` dv
        LEFT JOIN `tabVehicle` v ON v.name = dv.vehicle
        WHERE dv.date_expiration IS NOT NULL AND dv.date_expiration <= %s
        ORDER BY dv.date_expiration ASC
        LIMIT 10
        """,
        (in_30j,), as_dict=True,
    )
    for r in rows:
        if r.date_expiration:
            delta = (getdate(r.date_expiration) - today_d).days
            r["delta_jours"] = delta
            r["urgence"] = "expired" if delta < 0 else ("warning" if delta <= 30 else "ok")
            r["label"] = f"Expiré depuis {-delta}j" if delta < 0 else f"Expire dans {delta}j"
    return rows


def _repartition():
    """Répartition par marque, type carburant, conducteur."""
    if not frappe.db.exists("DocType", "Vehicle"):
        return {"par_marque": [], "par_carburant": [], "par_conducteur": []}

    par_marque = frappe.db.sql(
        "SELECT COALESCE(make, 'Non renseigné') AS k, COUNT(*) AS n FROM `tabVehicle` GROUP BY make ORDER BY n DESC",
        as_dict=True,
    )
    par_carburant = frappe.db.sql(
        "SELECT COALESCE(fuel_type, 'Non renseigné') AS k, COUNT(*) AS n FROM `tabVehicle` GROUP BY fuel_type ORDER BY n DESC",
        as_dict=True,
    )
    par_conducteur = frappe.db.sql(
        """
        SELECT COALESCE(e.employee_name, 'Sans conducteur assigné') AS k, COUNT(v.name) AS n
        FROM `tabVehicle` v
        LEFT JOIN `tabEmployee` e ON e.name = v.employee
        GROUP BY v.employee
        ORDER BY n DESC
        LIMIT 10
        """,
        as_dict=True,
    )
    return {
        "par_marque": par_marque,
        "par_carburant": par_carburant,
        "par_conducteur": par_conducteur,
    }


def _activite_vehicles(period):
    """Kilométrage + entretiens depuis Vehicle Log (si dispo)."""
    if not frappe.db.exists("DocType", "Vehicle Log"):
        return {"total_logs": 0, "km_total": 0, "carburant_total": 0, "depenses": 0, "recents": []}
    date_from = add_days(today(), -period)
    # Recupere seulement les champs garantis (varie selon ERPNext/HRMS version)
    try:
        rows = frappe.get_all(
            "Vehicle Log",
            filters={"date": [">=", date_from]},
            fields=["name", "license_plate", "date", "odometer", "fuel_qty", "price"],
            order_by="date desc",
            limit_page_length=20,
        )
    except Exception:
        rows = []
    for r in rows:
        r["vehicle"] = r.license_plate
        r["service_detail"] = ""
    return {
        "total_logs": len(rows),
        "km_total": sum(flt(r.odometer or 0) for r in rows),
        "carburant_total": sum(flt(r.fuel_qty or 0) for r in rows),
        "depenses": sum(flt(r.price or 0) for r in rows),
        "recents": rows[:10],
    }
