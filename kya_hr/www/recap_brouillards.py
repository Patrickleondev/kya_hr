import frappe
from frappe import _
from frappe.utils import add_days, getdate, formatdate, flt

no_cache = 1


def get_context(context):
    """Page récap hebdomadaire des brouillards de caisse.

    Accessible aux rôles : Directeur Général, DGA, DAAF, Comptable,
    Responsable RH, System Manager.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)

    allowed_roles = {
        "Directeur Général", "DGA", "DAAF", "Comptable",
        "Responsable RH", "System Manager", "HR Manager",
    }
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not allowed_roles.intersection(user_roles):
        frappe.throw(_("Accès refusé"), frappe.PermissionError)

    # ── Détermination de la semaine ──
    semaine = frappe.form_dict.get("semaine")  # format YYYY-Www
    today_d = getdate()
    if semaine and "-W" in semaine:
        try:
            year, wk = semaine.split("-W")
            year, wk = int(year), int(wk)
            # Lundi de la semaine ISO
            from datetime import date
            jan4 = date(year, 1, 4)
            week1_monday = add_days(jan4, -jan4.weekday())
            start = add_days(week1_monday, (wk - 1) * 7)
        except Exception:
            start = add_days(today_d, -today_d.weekday())
    else:
        start = add_days(today_d, -today_d.weekday())

    end = add_days(start, 4)  # vendredi

    iso_year, iso_week, _w = getdate(start).isocalendar()
    iso_tag = f"{iso_year}-W{iso_week:02d}"

    brouillards = frappe.get_all(
        "Brouillard Caisse",
        filters={
            "docstatus": 1,
            "date_brouillard": ["between", [start, end]],
        },
        fields=[
            "name", "date_brouillard", "caissiere_name",
            "total_entrees", "total_sorties", "solde_final",
            "total_reel_caisse", "statut",
        ],
        order_by="date_brouillard asc",
    )

    total_e = sum(flt(b.total_entrees or 0) for b in brouillards)
    total_s = sum(flt(b.total_sorties or 0) for b in brouillards)

    # Semaines précédentes (4 semaines navigation)
    prev_weeks = []
    for i in range(1, 5):
        d = add_days(start, -7 * i)
        y, w, _x = getdate(d).isocalendar()
        prev_weeks.append({
            "tag": f"{y}-W{w:02d}",
            "label": f"Sem. {w} ({formatdate(d)})",
        })

    # Semaine suivante (si pas dans le futur)
    next_start = add_days(start, 7)
    next_week = None
    if next_start <= today_d:
        y, w, _x = getdate(next_start).isocalendar()
        next_week = {
            "tag": f"{y}-W{w:02d}",
            "label": f"Sem. {w} ({formatdate(next_start)})",
        }

    context.brouillards = brouillards
    context.start = start
    context.end = end
    context.iso_tag = iso_tag
    context.iso_week = iso_week
    context.iso_year = iso_year
    context.total_e = total_e
    context.total_s = total_s
    context.solde = total_e - total_s
    context.nb = len(brouillards)
    context.start_label = formatdate(start)
    context.end_label = formatdate(end)
    context.prev_weeks = prev_weeks
    context.next_week = next_week
    context.no_breadcrumbs = True
