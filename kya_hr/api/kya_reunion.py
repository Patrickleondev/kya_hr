# pyright: reportMissingImports=false
"""Integration API for the external KYA-Reunion attendance system."""

import hmac
import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, now_datetime, today


DIRECTION_ROLES = {"DG", "Directeur Général", "System Manager", "Administrator", "Responsable RH", "HR Manager"}
STATUS_MAP = {
    "active": "Actif",
    "closed": "Clôturé",
    "expired": "Expiré",
    "expired_time": "Expiré",
    "deleted": "Supprimé",
}


def _request_ip():
    try:
        return frappe.local.request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or frappe.local.request.remote_addr
    except Exception:
        return ""


def _request_json():
    if getattr(frappe.local, "request", None):
        data = frappe.local.request.get_json(silent=True)
        if data:
            return data
    payload = frappe.form_dict.get("payload")
    if isinstance(payload, str) and payload.strip():
        return json.loads(payload)
    if isinstance(payload, dict):
        return payload
    return {}


def _json_dump(value):
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def _verify_secret(provided=None):
    expected = frappe.conf.get("kya_reunion_api_secret")
    if not expected:
        if frappe.session.user != "Guest" and {"System Manager", "Administrator"}.intersection(set(frappe.get_roles())):
            return
        frappe.throw(_("Secret d'intégration KYA-Reunion non configuré."), frappe.PermissionError)

    header_secret = ""
    try:
        header_secret = frappe.local.request.headers.get("X-KYA-Reunion-Secret") or ""
    except Exception:
        pass
    candidate = provided or header_secret or frappe.form_dict.get("secret") or ""
    if not hmac.compare_digest(str(expected), str(candidate)):
        frappe.throw(_("Secret d'intégration KYA-Reunion invalide."), frappe.PermissionError)


def _as_datetime(value):
    if not value:
        return None
    try:
        text = str(value).strip().replace("T", " ")
        if text.endswith("Z"):
            text = text[:-1]
        if "+" in text:
            text = text.split("+", 1)[0].strip()
        return get_datetime(text)
    except Exception:
        return None


def _presence_row(payload):
    return {
        "identity": payload.get("identity"),
        "nom_prenom": payload.get("nom_prenom") or payload.get("name") or payload.get("full_name"),
        "email": payload.get("email"),
        "telephone": payload.get("telephone") or payload.get("phone"),
        "poste": payload.get("poste") or payload.get("designation"),
        "entreprise": payload.get("entreprise") or payload.get("societe") or payload.get("company"),
        "signed_at": _as_datetime(payload.get("createdAt") or payload.get("created_at") or payload.get("signed_at")),
        "delay_minutes": cint(payload.get("delayMinutes") or payload.get("delay_minutes") or 0),
        "signature": payload.get("signature"),
        "raw_payload": _json_dump(payload),
    }


def _log_sync(external_token, action, status, payload=None, response=None, meeting=None):
    try:
        frappe.get_doc({
            "doctype": "KYA Reunion Sync Log",
            "external_token": external_token,
            "meeting": meeting,
            "action": action,
            "status": status,
            "source_system": "KYA-Reunion",
            "request_ip": _request_ip(),
            "received_at": now_datetime(),
            "payload": _json_dump(payload),
            "response": _json_dump(response),
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "KYA-Reunion sync log failed")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def sync_meeting(payload=None, secret=None):
    """Create/update one meeting mirrored from KYA-Reunion.

    Expected payload is the object returned by the external `/api/meetings/:token`
    endpoint, including `presences` when available.
    """
    _verify_secret(secret)
    data = json.loads(payload) if isinstance(payload, str) and payload.strip() else (payload or _request_json())
    if not isinstance(data, dict):
        frappe.throw(_("Payload réunion invalide."))

    external_token = (data.get("token") or data.get("external_token") or "").strip()
    if not external_token:
        frappe.throw(_("Le token de réunion externe est obligatoire."))

    try:
        name = frappe.db.exists("KYA Reunion Meeting", {"external_token": external_token})
        doc = frappe.get_doc("KYA Reunion Meeting", name) if name else frappe.new_doc("KYA Reunion Meeting")
        doc.external_token = external_token
        doc.source_system = "KYA-Reunion"
        doc.status = STATUS_MAP.get(str(data.get("status") or "").lower(), "Inconnu")
        doc.title = data.get("title") or external_token
        doc.meeting_type = data.get("type") or data.get("meeting_type")
        doc.location = data.get("location")
        doc.agenda = data.get("agenda")
        doc.start_at = _as_datetime(data.get("startAt") or data.get("start_at"))
        doc.end_at = _as_datetime(data.get("endAt") or data.get("end_at"))
        doc.expiry_mode = data.get("expiryMode") or data.get("expiry_mode")
        doc.limit_minutes = cint(data.get("limitMinutes") or data.get("limit_minutes") or 0)
        doc.tolerance_minutes = cint(data.get("toleranceMinutes") or data.get("tolerance_minutes") or 0)
        doc.scan_url = data.get("scanUrl") or data.get("scan_url")
        doc.qr_code_data_url = data.get("qrCodeDataUrl") or data.get("qr_code_data_url")
        doc.raw_payload = _json_dump(data)
        doc.last_sync = now_datetime()

        doc.set("presences", [])
        for presence in data.get("presences") or []:
            doc.append("presences", _presence_row(presence))
        doc.presence_count = len(doc.presences or [])

        if name:
            doc.save(ignore_permissions=True)
            action = "update"
        else:
            doc.insert(ignore_permissions=True)
            action = "insert"
        frappe.db.commit()

        response = {"ok": True, "meeting": doc.name, "action": action, "presence_count": doc.presence_count}
        _log_sync(external_token, action, "Succès", data, response, doc.name)
        return response
    except Exception as exc:
        _log_sync(external_token, "sync", "Erreur", data, {"error": str(exc)})
        raise


@frappe.whitelist()
def get_dashboard_stats(period=30):
    if not set(frappe.get_roles()).intersection(DIRECTION_ROLES):
        frappe.throw(_("Accès refusé"), frappe.PermissionError)

    period = cint(period or 30)
    start = add_days(today(), -period)
    rows = frappe.get_all(
        "KYA Reunion Meeting",
        filters={"start_at": [">=", start]},
        fields=["name", "title", "meeting_type", "status", "start_at", "presence_count", "last_sync"],
        order_by="start_at desc",
        limit=20,
    )
    total = len(rows)
    participants = sum(cint(row.presence_count) for row in rows)
    active = sum(1 for row in rows if row.status == "Actif")
    closed = sum(1 for row in rows if row.status == "Clôturé")
    by_type = {}
    for row in rows:
        key = row.meeting_type or "Non classé"
        by_type[key] = by_type.get(key, 0) + 1

    return {
        "total": total,
        "active": active,
        "closed": closed,
        "participants": participants,
        "by_type": by_type,
        "recent": rows,
    }


def get_summary_for_dashboard(date_from=None, date_to=None):
    meeting_conditions = ["docstatus < 2"]
    joined_conditions = ["m.docstatus < 2"]
    values = {}
    if date_from:
        meeting_conditions.append("start_at >= %(date_from)s")
        joined_conditions.append("m.start_at >= %(date_from)s")
        values["date_from"] = date_from
    if date_to:
        meeting_conditions.append("start_at <= %(date_to)s")
        joined_conditions.append("m.start_at <= %(date_to)s")
        values["date_to"] = date_to

    rows = frappe.db.sql(
        f"""
        SELECT status, COUNT(*) AS total, COALESCE(SUM(presence_count), 0) AS participants
        FROM `tabKYA Reunion Meeting`
        WHERE {' AND '.join(meeting_conditions)}
        GROUP BY status
        """,
        values,
        as_dict=True,
    )
    late_rows = frappe.db.sql(
        f"""
        SELECT COUNT(*) AS late_count, COALESCE(SUM(p.delay_minutes), 0) AS late_minutes
        FROM `tabKYA Reunion Presence` p
        INNER JOIN `tabKYA Reunion Meeting` m ON p.parent = m.name
        WHERE {' AND '.join(joined_conditions)}
          AND p.delay_minutes > 0
        """,
        values,
        as_dict=True,
    )

    by_status = {row.status or "Inconnu": {"total": cint(row.total), "participants": cint(row.participants)} for row in rows}
    late = late_rows[0] if late_rows else {}
    participants = sum(cint(row.participants) for row in rows)

    return {
        "active": cint(by_status.get("Actif", {}).get("total")),
        "closed": cint(by_status.get("Clôturé", {}).get("total")),
        "expired": cint(by_status.get("Expiré", {}).get("total")),
        "deleted": cint(by_status.get("Supprimé", {}).get("total")),
        "participants": participants,
        "late_count": cint(late.get("late_count")),
        "late_minutes": cint(late.get("late_minutes")),
        "by_status": by_status,
    }
