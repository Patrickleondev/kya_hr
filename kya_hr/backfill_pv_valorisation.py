"""Backfill valeur_totale_xof + nb_lignes on existing PV Sortie Materiel."""

import frappe


def run():
    pvs = frappe.get_all("PV Sortie Materiel", pluck="name")
    print(f"Backfill de {len(pvs)} PV(s)...")
    ok = 0
    for n in pvs:
        try:
            d = frappe.get_doc("PV Sortie Materiel", n)
            if hasattr(d, "_compute_valorisation"):
                d._compute_valorisation()
                d.db_set("valeur_totale_xof", d.valeur_totale_xof, update_modified=False)
                d.db_set("nb_lignes", d.nb_lignes, update_modified=False)
                for it in d.items:
                    it.db_update()
                ok += 1
                print(f"  ✓ {n}: {d.valeur_totale_xof:,.0f} XOF / {d.nb_lignes} lignes")
        except Exception as e:
            print(f"  ✗ {n}: {e}")
    frappe.db.commit()
    print(f"\n✅ Backfill terminé: {ok}/{len(pvs)}")
