"""Page : Dashboard Services Techniques & SAV.

Route : /services-techniques-dashboard

S'appuie sur les données réelles existantes — Équipes KYA et Tâches d'équipe
(objectifs des plans trimestriels). Le ticketing SAV dédié (tickets clients,
ordres de mission technique) n'a pas encore de modèle de données : la section
correspondante est signalée « à venir » plutôt que remplie de données fictives.
"""
from __future__ import annotations

import frappe


ACCESS_ROLES = {
    "System Manager", "Directeur General", "Directeur Général", "DG", "DGA",
    "Responsable Technique", "Chef de Projet", "Chef Service",
    "Chef Equipe", "Chef d'Equipe", "Responsable Equipe",
    "Responsable RH", "HR Manager", "Auditeur Interne", "Auditeur",
}


def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/services-techniques-dashboard"
        raise frappe.Redirect

    if not (set(frappe.get_roles(user)) & ACCESS_ROLES):
        frappe.throw(
            "Accès refusé - rôle Services Techniques ou Direction requis.",
            frappe.PermissionError,
        )

    context.page_title = "Dashboard Services Techniques & SAV"
    context.no_cache = 1
    context.no_breadcrumbs = True
    try:
        import json as _json
        context.overview_json = _json.dumps(get_st_overview(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "services-techniques-dashboard: overview")
    return context


# ════════════════════════════════════════════════════════════════════
#  Vue d'ensemble Services Techniques & SAV — données réelles
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
def get_st_overview() -> dict:
    """Indicateurs Services Techniques (équipes, tâches d'équipe par état, taux
    de réalisation, charge par équipe). Réel et défensif."""
    if not (set(frappe.get_roles(frappe.session.user)) & ACCESS_ROLES):
        frappe.throw("Accès réservé aux services techniques et à la Direction.", frappe.PermissionError)

    from frappe.utils import flt, today, formatdate

    # ── Équipes ──
    teams = []
    if _exists("Equipe KYA"):
        try:
            teams = frappe.get_all("Equipe KYA",
                fields=["name", "nom_equipe", "abreviation", "chef_equipe_name",
                        "est_active", "nombre_membres"],
                order_by="nom_equipe", limit_page_length=200)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "st-overview: teams")
    actives = [t for t in teams if t.est_active]

    # ── Tâches d'équipe ──
    taches = []
    if _exists("Tache Equipe"):
        try:
            taches = frappe.get_all("Tache Equipe",
                fields=["name", "equipe", "libelle", "resultat_libelle", "statut",
                        "taux_effectif", "taux_estime", "poids"],
                order_by="modified desc", limit_page_length=2000)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "st-overview: taches")

    # responsable par tâche (Attribution role=Responsable)
    resp_by_task = {}
    if _exists("Tache Equipe Attribution") and taches:
        try:
            for a in frappe.get_all("Tache Equipe Attribution",
                    filters={"role_attribution": "Responsable", "parenttype": "Tache Equipe"},
                    fields=["parent", "nom_employe"], limit_page_length=4000):
                resp_by_task.setdefault(a.parent, a.nom_employe)
        except Exception:
            pass

    def _st(t):
        return t.statut or "Non démarré"

    n_non = sum(1 for t in taches if _st(t) == "Non démarré")
    n_cours = sum(1 for t in taches if _st(t) == "En cours")
    n_term = sum(1 for t in taches if _st(t) == "Terminé")
    n_bloc = sum(1 for t in taches if _st(t) == "Bloqué")

    actifs = [t for t in taches if _st(t) != "Non démarré"]
    taux_moyen = round(sum(flt(t.taux_effectif) for t in actifs) / len(actifs)) if actifs else 0
    membres = sum(int(t.nombre_membres or 0) for t in actives)

    # ── Opérations terrain (doctypes prod, module CRM ; absents en local) ──
    # SAV / maintenance curative, ordres de mission, réceptions techniques,
    # enquêtes de satisfaction client. Tout est défensif (_exists / try-except).
    SAV_DT, MISSION_DT = "fiche technique curative", "fiche de mission"
    LAMP_DT, BATT_DT, ENQ_DT = "fiche_recep_tech_lampa", "fiche de recpt de batt", "EnqueteSatisfactionClient"

    def _safe_all(dt, fields, order_by="creation desc", limit=400):
        if not _exists(dt):
            return []
        try:
            return frappe.get_all(dt, fields=fields, order_by=order_by, limit_page_length=limit)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"st-overview: {dt}")
            return []

    fiches_sav = _safe_all(SAV_DT, ["name", "clientsite", "techname", "dateinter",
                                    "objinter", "etatsys", "creation"],
                           order_by="dateinter desc, creation desc")
    fiches_mission = _safe_all(MISSION_DT, ["name", "chef_mission", "destination", "objet",
                                            "date_emission", "workflow_state", "duree", "creation"],
                               order_by="date_emission desc, creation desc")
    n_sav = len(fiches_sav)
    n_mission = len(fiches_mission)
    n_recep = _count(LAMP_DT) + _count(BATT_DT)

    # Satisfaction client moyenne (/5) — scores texte "1".."5"
    enquetes = _safe_all(ENQ_DT, ["efficacite_installation", "efficacite_sav",
                                  "qualite_maintenance", "recommendations"])
    sat_vals = []
    for e in enquetes:
        for f in ("efficacite_sav", "qualite_maintenance", "efficacite_installation"):
            try:
                v = int(e.get(f))
                if 1 <= v <= 5:
                    sat_vals.append(v)
            except (TypeError, ValueError):
                pass
    sat_avg = round(sum(sat_vals) / len(sat_vals), 1) if sat_vals else 0

    # ── Hero (6) — priorité aux ops terrain réelles ──
    hero = [
        {"label": "Interventions SAV", "value": str(n_sav), "sub": "fiches curatives", "icon": "wrench"},
        {"label": "Ordres de mission", "value": str(n_mission), "sub": "fiches de mission", "icon": "route"},
        {"label": "Réceptions techniques", "value": str(n_recep), "sub": "lampadaires + batteries", "icon": "check"},
        {"label": "Équipes techniques", "value": str(len(actives)), "unit": f"/ {len(teams)}",
         "sub": f"{membres} membres", "icon": "users"},
        {"label": "Satisfaction client", "value": (str(sat_avg) if sat_avg else "—"),
         "unit": ("/ 5" if sat_avg else ""), "sub": f"{len(enquetes)} enquêtes", "icon": "gauge"},
        {"label": "Tâches d'équipe en cours", "value": str(n_cours),
         "sub": f"{n_bloc} bloquées", "icon": "alert"},
    ]

    # ── Tables ops terrain ──
    from frappe.utils import formatdate as _fd
    sav_rows = []
    for f in fiches_sav[:8]:
        sav_rows.append({
            "client": f.clientsite or "—",
            "tech": f.techname or "—",
            "objet": f.objinter or "—",
            "date": _fd(f.dateinter, "dd/MM/y") if f.dateinter else "—",
            "etat": f.etatsys or "—",
            "accent": "ok" if (f.etatsys or "").lower().startswith("fonction") else "wait",
        })
    mission_rows = []
    for m in fiches_mission[:8]:
        st = m.workflow_state or "—"
        mission_rows.append({
            "ref": m.name, "chef": m.chef_mission or "—",
            "destination": m.destination or "—", "objet": m.objet or "—",
            "date": _fd(m.date_emission, "dd/MM/y") if m.date_emission else "—",
            "etat": st,
            "accent": "ok" if st.lower() in ("approved", "approuvé", "approuve") else ("bad" if "reject" in st.lower() else "wait"),
        })

    # ── Tâches techniques en cours (table) ──
    st_badge = {"En cours": "wait", "Bloqué": "bad", "Terminé": "ok", "Non démarré": "slate"}
    encours = [t for t in taches if _st(t) in ("En cours", "Bloqué")]
    tache_rows = []
    for t in encours[:10]:
        tache_rows.append({
            "equipe": t.equipe or "—",
            "objet": t.libelle or t.resultat_libelle or "—",
            "responsable": resp_by_task.get(t.name, "—"),
            "taux": str(round(flt(t.taux_effectif))) + " %",
            "etat": _st(t), "accent": st_badge.get(_st(t), "wait"),
        })

    # ── Charge par équipe (table) ──
    by_team = {}
    for t in taches:
        eq = t.equipe or "—"
        agg = by_team.setdefault(eq, {"cours": 0, "term": 0, "sum": 0.0, "n": 0})
        s = _st(t)
        if s == "En cours" or s == "Bloqué":
            agg["cours"] += 1
        elif s == "Terminé":
            agg["term"] += 1
        if s != "Non démarré":
            agg["sum"] += flt(t.taux_effectif)
            agg["n"] += 1
    team_rows = []
    for t in actives:
        key = t.nom_equipe or t.abreviation or t.name
        agg = by_team.get(key) or by_team.get(t.abreviation) or {"cours": 0, "term": 0, "sum": 0.0, "n": 0}
        charge = round(agg["sum"] / agg["n"]) if agg["n"] else 0
        team_rows.append({
            "equipe": t.nom_equipe or "—", "chef": t.chef_equipe_name or "—",
            "encours": agg["cours"], "cloturees": agg["term"], "charge": charge,
        })
    team_rows.sort(key=lambda r: (r["encours"], r["charge"]), reverse=True)

    # ── Charts ──
    etats = {"labels": ["Non démarré", "En cours", "Terminé", "Bloqué"],
             "data": [n_non, n_cours, n_term, n_bloc]}
    charge = {"labels": [r["equipe"] for r in team_rows[:8]],
              "data": [r["charge"] for r in team_rows[:8]]}

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero, "sav_rows": sav_rows, "mission_rows": mission_rows,
        "tache_rows": tache_rows, "team_rows": team_rows[:10],
        "etats": etats, "charge": charge,
        "sav_label": f"{n_sav} interventions",
        "mission_label": f"{n_mission} missions",
        "ouverts_label": f"{n_cours} en cours · {n_bloc} bloquées",
        "equipes_label": f"{len(actives)} équipes",
        "sav_note": "Les interventions SAV proviennent des fiches techniques curatives "
                    "(saisie terrain) et les déplacements des fiches de mission. Le suivi "
                    "des tâches d'équipe s'appuie sur les plans trimestriels.",
    }
