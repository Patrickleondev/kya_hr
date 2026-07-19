"""Pont Employee (ERPNext) → Salarie KYA (registre RH).

Jusqu'ici la RH saisissait DEUX FOIS la même personne : une fiche `Employee`
pour tout ce qui touche aux congés, présences et circuits de validation, et
une fiche `Salarie KYA` pour le registre du personnel et les tableaux de bord.
Rien ne reliait les deux : deux matricules, deux orthographes, deux dates
d'embauche possibles.

Ce module supprime la double saisie : la fiche Employee devient la SOURCE, le
registre `Salarie KYA` se crée et se met à jour tout seul.

Règle de sécurité absolue : on ne CONTREDIT jamais une saisie de la RH. À la
création on renseigne tout ce qu'on sait ; ensuite on ne remplit que les
champs restés VIDES. Les informations que l'Employee ne connaît pas (salaire,
catégorie, niveau d'études, photo…) restent la propriété de la RH.
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate

# ── Correspondances ERPNext → registre RH ────────────────────────────────
_SEXE = {"Male": "M", "Female": "F", "Homme": "M", "Femme": "F"}

_CONTRAT = {
    "cdi": "CDI",
    "cdd": "CDD",
    "stage": "Stagiaire",
    "stagiaire": "Stagiaire",
    "prestataire de services": "Prestataire",
    "prestataire": "Prestataire",
    "interim": "Intérim",
    "intérim": "Intérim",
}

# Employee.status : Active / Inactive / Suspended / Left
_STATUT = {"left": "Sorti"}

_MATRIMONIAL = {
    ("single", "M"): "CELIBATAIRE", ("single", "F"): "CELIBATAIRE",
    ("married", "M"): "MARIE", ("married", "F"): "MARIEE",
    ("divorced", "M"): "DIVORCE", ("divorced", "F"): "DIVORCEE",
    ("widowed", "M"): "VEUF", ("widowed", "F"): "VEUVE",
}


def _matricule(emp):
    """Matricule du registre. On privilégie le numéro saisi par la RH ; à
    défaut l'identifiant Employee, qui est unique par construction."""
    return (emp.get("employee_number") or "").strip() or emp.get("name")


def _departement_kya(dep_erpnext):
    """Rapproche le département ERPNext (« EQUIPE INFORMATIQUE - KYA ») d'un
    `Departement KYA`. Aucune correspondance trouvée → on laisse vide plutôt
    que de rattacher la personne au mauvais service."""
    if not dep_erpnext:
        return None
    base = dep_erpnext.rsplit(" - ", 1)[0].strip()
    for champ in ("name", "nom_departement"):
        try:
            trouve = frappe.db.get_value("Departement KYA", {champ: base}, "name")
            if trouve:
                return trouve
        except Exception:
            pass
    try:
        cands = frappe.get_all("Departement KYA", pluck="name", limit_page_length=0)
        base_n = base.lower()
        for c in cands:
            if c.lower() == base_n:
                return c
    except Exception:
        pass
    return None


def _cle_nom(txt):
    """Nom réduit à ses lettres, sans casse ni accents ni ordre : « Yao Ketowoglo
    AZOUMAH » et « AZOUMAH Yao Ketowoglo » doivent se reconnaître."""
    import unicodedata

    if not txt:
        return ""
    t = unicodedata.normalize("NFKD", str(txt))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    mots = sorted(m for m in "".join(c if c.isalnum() else " " for c in t).split() if m)
    return " ".join(mots)


def _retrouver_salarie(emp, vals):
    """Fiche `Salarie KYA` déjà existante pour cet employé, ou None.

    Trois passes, de la plus sûre à la plus tolérante. La dernière (par nom)
    est INDISPENSABLE : le registre a été saisi à la main avec ses propres
    matricules (10001, 10002…) qui ne correspondent pas aux identifiants
    Employee. Sans elle, le peuplement créerait un DOUBLON pour chaque
    personne déjà enregistrée.
    """
    trouve = frappe.db.get_value("Salarie KYA", {"employee": emp.get("name")}, "name")
    if trouve:
        return trouve
    trouve = frappe.db.get_value("Salarie KYA", {"matricule": _matricule(emp)}, "name")
    if trouve:
        return trouve

    cible = _cle_nom(vals.get("nom_complet"))
    if not cible:
        return None
    for row in frappe.get_all("Salarie KYA",
                              fields=["name", "nom_complet", "nom", "prenoms", "employee"],
                              limit_page_length=0):
        if row.get("employee"):
            continue  # déjà rattaché à un autre employé
        if _cle_nom(row.get("nom_complet")) == cible:
            return row["name"]
        if _cle_nom("{0} {1}".format(row.get("nom") or "", row.get("prenoms") or "")) == cible:
            return row["name"]
    return None


def _valeurs_depuis_employee(emp):
    sexe = _SEXE.get(emp.get("gender") or "")
    etype = (emp.get("employment_type") or "").strip().lower()
    statut_mat = _MATRIMONIAL.get(
        ((emp.get("marital_status") or "").strip().lower(), sexe or "M"))

    vals = {
        "nom": (emp.get("last_name") or "").strip(),
        "prenoms": (emp.get("first_name") or "").strip(),
        "nom_complet": (emp.get("employee_name") or "").strip(),
        "sexe": sexe,
        "date_naissance": emp.get("date_of_birth"),
        "date_embauche": emp.get("date_of_joining"),
        "poste_occupe": (emp.get("designation") or "").strip(),
        "departement": _departement_kya(emp.get("department")),
        "type_contrat": _CONTRAT.get(etype),
        "contact_telephonique": (emp.get("cell_number") or "").strip(),
        "statut_matrimonial": statut_mat,
        "statut_emploi": _STATUT.get((emp.get("status") or "").strip().lower(), "Actif"),
        "date_debauchage": emp.get("relieving_date"),
    }
    return {k: v for k, v in vals.items() if v not in (None, "")}


def sync_salarie_from_employee(doc, method=None):
    """Crée ou complète la fiche `Salarie KYA` correspondant à un Employee.

    Branché sur les événements Employee (voir hooks.py). Ne lève jamais : un
    incident de synchronisation ne doit pas empêcher d'enregistrer un employé.
    """
    try:
        emp = doc.as_dict() if hasattr(doc, "as_dict") else dict(doc)
        _sync_un(emp)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "rh_sync.sync_salarie_from_employee")


def _sync_un(emp, ecraser=False):
    """Retourne 'cree', 'complete' ou 'inchange'."""
    vals = _valeurs_depuis_employee(emp)
    if not vals.get("nom_complet"):
        return "inchange"

    nom_salarie = _retrouver_salarie(emp, vals)

    if not nom_salarie:
        doc = frappe.get_doc(dict(
            doctype="Salarie KYA", matricule=_matricule(emp),
            employee=emp.get("name"), **vals))
        doc.flags.ignore_permissions = True
        doc.insert()
        return "cree"

    sal = frappe.get_doc("Salarie KYA", nom_salarie)
    change = False
    if not sal.get("employee"):
        sal.employee = emp.get("name")
        change = True
    for champ, valeur in vals.items():
        actuel = sal.get(champ)
        # On ne remplace JAMAIS une valeur saisie par la RH.
        if ecraser or actuel in (None, "", 0):
            if actuel != valeur:
                sal.set(champ, valeur)
                change = True
    if not change:
        return "inchange"
    sal.flags.ignore_permissions = True
    sal.save()
    return "complete"


@frappe.whitelist()
def seeder_depuis_employees(dry_run=1, inclure_inactifs=1):
    """Alimente le registre `Salarie KYA` à partir de TOUS les Employee.

    À lancer une fois après le déploiement : la RH n'a alors plus qu'à
    compléter ce que la fiche Employee ne contient pas (salaire, catégorie,
    photo…) au lieu de tout ressaisir.

    `dry_run=1` (défaut) : simule et rend le détail, sans rien écrire.
    """
    if not ({"System Manager", "Responsable RH", "HR Manager", "Directeur Général"}
            & set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Réservé aux Ressources Humaines."), frappe.PermissionError)

    dry_run = int(dry_run or 0)
    filtres = {} if int(inclure_inactifs or 0) else {"status": "Active"}
    champs = ["name", "employee_number", "employee_name", "first_name", "last_name",
              "gender", "date_of_birth", "date_of_joining", "designation",
              "department", "status", "cell_number", "employment_type",
              "marital_status", "relieving_date"]
    employes = frappe.get_all("Employee", filters=filtres, fields=champs,
                              limit_page_length=0) or []

    res = {"total": len(employes), "crees": 0, "completes": 0, "inchanges": 0,
           "sans_departement": [], "detail": [], "dry_run": bool(dry_run)}

    for emp in employes:
        vals = _valeurs_depuis_employee(emp)
        if not vals.get("nom_complet"):
            continue
        if emp.get("department") and not vals.get("departement"):
            res["sans_departement"].append(emp.get("employee_name"))

        if dry_run:
            action = "complete" if _retrouver_salarie(emp, vals) else "cree"
        else:
            action = _sync_un(emp)

        res[{"cree": "crees", "complete": "completes", "inchange": "inchanges"}[action]] += 1
        res["detail"].append({"employee": emp.name, "nom": emp.employee_name,
                              "matricule": _matricule(emp), "action": action,
                              "departement": vals.get("departement") or "—"})

    if not dry_run:
        frappe.db.commit()
    return res
