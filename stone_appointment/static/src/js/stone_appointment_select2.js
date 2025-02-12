$('#slot_dates').select2( {
    theme: "bootstrap-5",
    containerCssClass: "select2--small", // For Select2 v4.0
    selectionCssClass: "select2--small", // For Select2 v4.1
    dropdownCssClass: "select2--small",
    dropdownParent: $("#slot_dates").parent(),
    width: $(this).data('width') ? $(this).data('width'):$(this).hasClass('w-100') ? '100%' : 'style',
    placeholder: $(this).data('placeholder'),
    allowClear: true
} );