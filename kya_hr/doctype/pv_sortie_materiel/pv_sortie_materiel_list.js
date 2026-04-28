// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['PV Sortie Materiel'] = frappe.listview_settings['PV Sortie Materiel'] || {};
(function() {
  const prev_onload = frappe.listview_settings['PV Sortie Materiel'].onload;
  frappe.listview_settings['PV Sortie Materiel'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouveau PV Sortie'), () => {
      window.open('/pv-sortie-materiel/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();
