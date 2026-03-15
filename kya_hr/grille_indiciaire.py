"""
Grille de classification / valeur indiciaire / points d'indice
KYA-Energy Group — Article 13 du Règlement Intérieur

4 catégories : AE (A-D), AM (E-G), C (H-L), HC (M-P)
16 classes (A → P), 8 échelons (1 → 8)
"""

# fmt: off
GRILLE = {
    # ── Agents d'exécution (AE) ──
    "A": [270, 276, 282, 288, 294, 300, 306, 312],
    "B": [319, 326, 333, 340, 347, 354, 361, 368],
    "C": [377, 386, 395, 404, 413, 422, 431, 440],
    "D": [450, 460, 470, 480, 490, 500, 510, 520],
    # ── Agents de maîtrise (AM) ──
    "E": [540, 553, 566, 579, 592, 605, 618, 631],
    "F": [644, 657, 670, 683, 697, 710, 723, 736],
    "G": [749, 762, 775, 789, 802, 815, 828, 841],
    # ── Cadres (C) ──
    "H": [855,  868,  881,  895,  908,  921,  935,  948],
    "I": [864,  885,  907,  928,  949,  970,  992, 1013],
    "J": [1035, 1058, 1080, 1102, 1124, 1147, 1169, 1191],
    "K": [1214, 1238, 1261, 1284, 1308, 1331, 1354, 1377],
    "L": [1402, 1426, 1450, 1475, 1499, 1523, 1547, 1572],
    # ── Hauts Cadres (HC) ──
    "M": [1728, 1777, 1825, 1874, 1922, 1971, 2019, 2068],
    "N": [2117, 2167, 2217, 2266, 2316, 2365, 2415, 2464],
    "O": [2465, 2516, 2567, 2617, 2668, 2718, 2769, 2819],
    "P": [2871, 2922, 2974, 3026, 3077, 3129, 3180, 3232],
}
# fmt: on

CLASSE_CATEGORIE = {
    "A": "Agents d'exécution (AE)", "B": "Agents d'exécution (AE)",
    "C": "Agents d'exécution (AE)", "D": "Agents d'exécution (AE)",
    "E": "Agents de maîtrise", "F": "Agents de maîtrise", "G": "Agents de maîtrise",
    "H": "Cadres", "I": "Cadres", "J": "Cadres", "K": "Cadres", "L": "Cadres",
    "M": "Hauts Cadres (HC)", "N": "Hauts Cadres (HC)",
    "O": "Hauts Cadres (HC)", "P": "Hauts Cadres (HC)",
}


def get_valeur_indiciaire(classe, echelon):
    """Retourne les points d'indice pour une classe et un échelon donnés."""
    if not classe or not echelon:
        return 0
    echelon = int(echelon)
    if classe not in GRILLE or echelon < 1 or echelon > 8:
        return 0
    return GRILLE[classe][echelon - 1]


def calculer_indice_employee(doc, method=None):
    """Hook before_save sur Employee : recalcule automatiquement custom_kya_indice."""
    classe = doc.get("custom_kya_classe")
    echelon = doc.get("custom_kya_echelon")
    if classe and echelon:
        indice = get_valeur_indiciaire(classe, int(echelon))
        doc.custom_kya_indice = indice
        # Auto-set la catégorie si elle est vide ou incohérente
        categorie_attendue = CLASSE_CATEGORIE.get(classe)
        if categorie_attendue and doc.get("custom_kya_categorie") != categorie_attendue:
            doc.custom_kya_categorie = categorie_attendue
    elif not classe or not echelon:
        doc.custom_kya_indice = 0
