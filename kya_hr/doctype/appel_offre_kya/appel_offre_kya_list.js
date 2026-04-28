// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['Appel Offre KYA'] = frappe.listview_settings['Appel Offre KYA'] || {};
(function() {
  const prev_onload = frappe.listview_settings['Appel Offre KYA'].onload;
  frappe.listview_settings['Appel Offre KYA'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouvel Appel d'Offre'), () => {
      window.open('/appel-offre/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();
