/**
 * Employee client script — real-time valeur indiciaire calculation
 * KYA-Energy Group, Article 13 du Règlement Intérieur
 */
frappe.ui.form.on('Employee', {
    custom_kya_classe: function(frm) {
        calculer_indice(frm);
    },
    custom_kya_echelon: function(frm) {
        calculer_indice(frm);
    }
});

function calculer_indice(frm) {
    var classe = frm.doc.custom_kya_classe;
    var echelon = frm.doc.custom_kya_echelon;

    if (!classe || !echelon) {
        frm.set_value('custom_kya_indice', 0);
        frm.set_value('custom_kya_categorie', '');
        return;
    }

    // Grille indiciaire — 16 classes × 8 échelons
    var GRILLE = {
        'A': [270, 276, 282, 288, 294, 300, 306, 312],
        'B': [319, 326, 333, 340, 347, 354, 361, 368],
        'C': [377, 386, 395, 404, 413, 422, 431, 440],
        'D': [450, 460, 470, 480, 490, 500, 510, 520],
        'E': [540, 553, 566, 579, 592, 605, 618, 631],
        'F': [644, 657, 670, 683, 697, 710, 723, 736],
        'G': [749, 762, 775, 789, 802, 815, 828, 841],
        'H': [855, 868, 881, 895, 908, 921, 935, 948],
        'I': [864, 885, 907, 928, 949, 970, 992, 1013],
        'J': [1035, 1058, 1080, 1102, 1124, 1147, 1169, 1191],
        'K': [1214, 1238, 1261, 1284, 1308, 1331, 1354, 1377],
        'L': [1402, 1426, 1450, 1475, 1499, 1523, 1547, 1572],
        'M': [1728, 1777, 1825, 1874, 1922, 1971, 2019, 2068],
        'N': [2117, 2167, 2217, 2266, 2316, 2365, 2415, 2464],
        'O': [2465, 2516, 2567, 2617, 2668, 2718, 2769, 2819],
        'P': [2871, 2922, 2974, 3026, 3077, 3129, 3180, 3232]
    };

    var CLASSE_CATEGORIE = {
        'A': "Agents d'exécution (AE)", 'B': "Agents d'exécution (AE)",
        'C': "Agents d'exécution (AE)", 'D': "Agents d'exécution (AE)",
        'E': "Agents de maîtrise", 'F': "Agents de maîtrise", 'G': "Agents de maîtrise",
        'H': "Cadres", 'I': "Cadres", 'J': "Cadres", 'K': "Cadres", 'L': "Cadres",
        'M': "Hauts Cadres (HC)", 'N': "Hauts Cadres (HC)",
        'O': "Hauts Cadres (HC)", 'P': "Hauts Cadres (HC)"
    };

    var ech = parseInt(echelon);
    if (GRILLE[classe] && ech >= 1 && ech <= 8) {
        frm.set_value('custom_kya_indice', GRILLE[classe][ech - 1]);
        frm.set_value('custom_kya_categorie', CLASSE_CATEGORIE[classe] || '');
    } else {
        frm.set_value('custom_kya_indice', 0);
        frm.set_value('custom_kya_categorie', '');
    }
}
