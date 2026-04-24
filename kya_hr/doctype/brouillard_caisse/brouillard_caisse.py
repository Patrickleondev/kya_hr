import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class BrouillardCaisse(Document):
    """Brouillard de Caisse — saisie quotidienne par la Caissière.

    Workflow: Caissière (saisit) → Comptable (vise) → DFC (valide).
    Totaux calculés + solde ligne-à-ligne côté serveur pour cohérence,
    même si le JS fait la même chose côté client.
    """

    def validate(self):
        self._compute_line_soldes()
        self._compute_totals()
        self._auto_sign_caissiere()

    def _compute_line_soldes(self):
        solde = flt(self.solde_precedent or 0)
        for ligne in (self.lignes or []):
            solde += flt(ligne.entree or 0) - flt(ligne.sortie or 0)
            ligne.solde = solde

    def _compute_totals(self):
        self.total_entrees = sum(flt(l.entree or 0) for l in (self.lignes or []))
        self.total_sorties = sum(flt(l.sortie or 0) for l in (self.lignes or []))
        self.solde_final = flt(self.solde_precedent or 0) + flt(self.total_entrees) - flt(self.total_sorties)

    def _auto_sign_caissiere(self):
        if self.caissiere and not self.signataire_caissiere:
            emp_name = frappe.db.get_value("Employee", self.caissiere, "employee_name")
            self.signataire_caissiere = emp_name or self.caissiere
            self.date_signature_caissiere = today()


# ─── Point hebdomadaire DG ──────────────────────────────────────────────
def send_weekly_dg_summary():
    """Scheduler vendredi soir: récap des brouillards approuvés de la semaine
    envoyé au DG + DGA.

    Déclenché par hooks.py -> scheduler_events.cron "0 17 * * 5".
    """
    from frappe.utils import add_days, getdate, formatdate

    today_d = getdate()
    # Semaine = lundi → vendredi (indépendamment du jour de déclenchement)
    weekday = today_d.weekday()  # lundi=0 ... vendredi=4
    start = add_days(today_d, -weekday)
    end = add_days(start, 4)

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

    if not brouillards:
        return

    # Destinataires : DG + DGA (par rôle)
    recipients = _get_users_with_roles(["Directeur Général", "DGA"])
    if not recipients:
        return

    total_e = sum(flt(b.total_entrees or 0) for b in brouillards)
    total_s = sum(flt(b.total_sorties or 0) for b in brouillards)

    rows = "".join(
        "<tr><td style='padding:6px 10px;border-bottom:1px solid #eee;'>{d}</td>"
        "<td style='padding:6px 10px;border-bottom:1px solid #eee;'>{n}</td>"
        "<td style='padding:6px 10px;border-bottom:1px solid #eee;'>{c}</td>"
        "<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right;'>{e}</td>"
        "<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right;'>{so}</td>"
        "<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right;'><b>{sf}</b></td>"
        "</tr>".format(
            d=formatdate(b.date_brouillard),
            n=b.name,
            c=b.caissiere_name or "",
            e="{:,.0f}".format(flt(b.total_entrees or 0)).replace(",", " "),
            so="{:,.0f}".format(flt(b.total_sorties or 0)).replace(",", " "),
            sf="{:,.0f}".format(flt(b.solde_final or 0)).replace(",", " "),
        )
        for b in brouillards
    )

    base = frappe.utils.get_url()
    message = (
        "<div style='font-family:Arial,sans-serif;max-width:780px;margin:0 auto;'>"
        "<div style='background:linear-gradient(135deg,#009688,#00bcd4);padding:24px;"
        "border-radius:12px 12px 0 0;text-align:center;'>"
        f"<img src='{base}/assets/kya_hr/images/kya_logo.png' width='60' style='margin-bottom:8px;'>"
        "<h2 style='color:white;margin:0;'>Point Hebdomadaire — Caisse</h2>"
        f"<p style='color:white;margin:6px 0 0;'>Semaine du {formatdate(start)} au {formatdate(end)}</p>"
        "</div>"
        "<div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>"
        "<p>Bonjour,</p>"
        f"<p>Récapitulatif des <b>{len(brouillards)}</b> brouillards de caisse approuvés cette semaine.</p>"
        "<table style='width:100%;border-collapse:collapse;margin:14px 0;font-size:13px;'>"
        "<thead><tr style='background:#009688;color:white;'>"
        "<th style='padding:8px 10px;text-align:left;'>Date</th>"
        "<th style='padding:8px 10px;text-align:left;'>Réf.</th>"
        "<th style='padding:8px 10px;text-align:left;'>Caissier(ère)</th>"
        "<th style='padding:8px 10px;text-align:right;'>Entrées</th>"
        "<th style='padding:8px 10px;text-align:right;'>Sorties</th>"
        "<th style='padding:8px 10px;text-align:right;'>Solde Final</th>"
        f"</tr></thead><tbody>{rows}</tbody>"
        "<tfoot><tr style='background:#f1f8e9;font-weight:700;'>"
        "<td colspan='3' style='padding:8px 10px;'>Totaux</td>"
        f"<td style='padding:8px 10px;text-align:right;'>{total_e:,.0f} XOF</td>"
        f"<td style='padding:8px 10px;text-align:right;'>{total_s:,.0f} XOF</td>"
        f"<td style='padding:8px 10px;text-align:right;'>{(total_e-total_s):,.0f} XOF</td>"
        "</tr></tfoot></table>"
        "</div></div>"
    ).replace(",", " ")

    frappe.sendmail(
        recipients=recipients,
        subject=f"Point hebdo caisse — semaine du {formatdate(start)} au {formatdate(end)}",
        message=message,
        reference_doctype="Brouillard Caisse",
        now=False,
    )


def _get_users_with_roles(roles):
    if not roles:
        return []
    users = frappe.get_all(
        "Has Role",
        filters={"role": ["in", roles], "parenttype": "User"},
        fields=["parent"],
        distinct=True,
    )
    emails = []
    for u in users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email and email not in emails and u.parent not in ("Guest", "Administrator"):
            emails.append(email)
    return emails
