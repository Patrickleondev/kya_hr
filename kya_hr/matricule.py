import frappe


def auto_generate_matricule(doc, method=None):
    """
    Auto-génère un matricule KYA pour les nouveaux employés si le champ est vide.
    Format : KEG-XXXXX (incrémenté à partir du dernier matricule existant).
    Stagiaires : STG-XXXXX.
    """
    if doc.custom_matricule_kya:
        return  # Déjà renseigné, ne pas écraser

    prefix = "STG" if doc.employment_type == "Stage" else "KEG"
    last = _get_last_matricule(prefix)
    next_num = last + 1
    doc.custom_matricule_kya = f"{prefix}-{next_num:05d}"


def _get_last_matricule(prefix):
    """Récupère le dernier numéro de matricule pour un préfixe donné."""
    result = frappe.db.sql("""
        SELECT custom_matricule_kya
        FROM tabEmployee
        WHERE custom_matricule_kya LIKE %s
        ORDER BY custom_matricule_kya DESC
        LIMIT 1
    """, (f"{prefix}-%",), as_dict=True)

    if not result:
        return 0

    last_mat = result[0].get("custom_matricule_kya", "")
    try:
        return int(last_mat.split("-")[-1])
    except (ValueError, IndexError):
        return 0
