// Auto-generated KYA: bouton Saisir via formulaire web dans la list view
frappe.listview_settings['Demande Achat KYA'] = frappe.listview_settings['Demande Achat KYA'] || {};
(function() {
  const prev_onload = frappe.listview_settings['Demande Achat KYA'].onload;
  frappe.listview_settings['Demande Achat KYA'].onload = function(listview) {
    if (typeof prev_onload === 'function') { try { prev_onload(listview); } catch (e) {} }
    listview.page.add_inner_button(__('Nouvelle Demande d'Achat'), () => {
      window.open('/demande-achat/new', '_blank');
    }).addClass('btn-primary').css({'background-color': '#e65100', 'color': 'white', 'font-weight': '600'});
  };
})();
