// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['Bon Commande KYA'] = frappe.listview_settings['Bon Commande KYA'] || {};
(function() {
  const prev_onload = frappe.listview_settings['Bon Commande KYA'].onload;
  frappe.listview_settings['Bon Commande KYA'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouveau Bon de Commande'), () => {
      window.open('/bon-commande/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();
