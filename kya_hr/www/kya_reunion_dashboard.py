"""Dashboard centralisé KYA-Reunion / KYA-Digi-Presence.

Affiche les données synchronisées depuis KYA-Digi-Presence (anciennement
KYA-Reunion) avec mise à jour temps réel via frappe.publish_realtime
(événement 'kya_reunion_meeting_synced' déclenché par kya_reunion.sync_meeting).
"""
import frappe
from frappe import _
from frappe.utils import cint, format_datetime, add_days, today

no_cache = 1

_ALLOWED_ROLES = {
    "Directeur Général", "DGA", "DAAF", "DFC",
    "Auditeur Interne", "HR Manager", "Responsable RH",
    "System Manager",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles())):
        frappe.throw(_("Accès réservé à la Direction / RH / Audit."), frappe.PermissionError)

    period = cint(frappe.form_dict.get("period") or 30)
    start = add_days(today(), -period)

    meetings = frappe.get_all(
        "KYA Reunion Meeting",
        filters={"start_at": [">=", start]},
        fields=[
            "name", "external_token", "title", "meeting_type", "location",
            "status", "start_at", "end_at", "presence_count", "last_sync",
        ],
        order_by="start_at desc",
        limit=50,
    )
    for m in meetings:
        m["start_at_label"] = format_datetime(m.get("start_at"), "dd/MM/yyyy HH:mm") if m.get("start_at") else ""
        m["last_sync_label"] = format_datetime(m.get("last_sync"), "dd/MM/yyyy HH:mm") if m.get("last_sync") else ""

    # KPIs
    total = len(meetings)
    total_presences = sum(cint(m.get("presence_count") or 0) for m in meetings)
    actifs = sum(1 for m in meetings if m.get("status") == "Actif")
    clotures = sum(1 for m in meetings if m.get("status") == "Clôturé")

    # Répartition par type
    by_type = {}
    for m in meetings:
        t = m.get("meeting_type") or "Non classé"
        by_type[t] = by_type.get(t, 0) + 1

    # Logs récents
    sync_logs = frappe.get_all(
        "KYA Reunion Sync Log",
        fields=["name", "external_token", "action", "status", "received_at"],
        order_by="received_at desc",
        limit=15,
    )
    for log in sync_logs:
        log["received_at_label"] = format_datetime(log.get("received_at"), "dd/MM/yyyy HH:mm:ss") if log.get("received_at") else ""

    # --- Visites des invités (KYA Guest Visit) ---
    visits = []
    visits_total = 0
    visits_presents = 0
    if frappe.db.exists("DocType", "KYA Guest Visit"):
        visits = frappe.get_all(
            "KYA Guest Visit",
            filters={"check_in": [">=", start]},
            fields=[
                "name", "nom", "prenom", "profession", "service_id",
                "personne_visitee", "motif", "statut", "check_in", "check_out",
            ],
            order_by="check_in desc",
            limit=50,
        )
        for v in visits:
            v["check_in_label"] = format_datetime(v.get("check_in"), "dd/MM/yyyy HH:mm") if v.get("check_in") else ""
            v["check_out_label"] = format_datetime(v.get("check_out"), "dd/MM/yyyy HH:mm") if v.get("check_out") else ""
            v["nom_complet"] = (" ".join([v.get("prenom") or "", v.get("nom") or ""])).strip() or "—"
            v["present"] = bool(v.get("check_in") and not v.get("check_out"))
        visits_total = len(visits)
        visits_presents = sum(1 for v in visits if v["present"])

    context.period = period
    context.meetings = meetings
    context.sync_logs = sync_logs
    context.visits = visits
    context.stats = {
        "total": total,
        "total_presences": total_presences,
        "actifs": actifs,
        "clotures": clotures,
        "visits_total": visits_total,
        "visits_presents": visits_presents,
    }
    context.by_type = by_type
    context.no_breadcrumbs = True
