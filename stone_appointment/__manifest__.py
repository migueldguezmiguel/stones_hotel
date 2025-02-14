# -*- coding: utf-8 -*-
{
    'name': 'Custom Appointment',
    'version': '17.0.2.10',
    'summary': """ Custom Appointment Summary """,
    'author': 'Miguel Miguel',
    'website': 'https://miguel.odoo.com',
    'category': 'Uncategorized',
    'depends': [
        'base', 
        'calendar',
        'portal',
        'sale',
        'appointment', 
        'website_appointment',
        'website_enterprise',        
    ],
    "data": [
        "security/ir.model.access.csv",
        'data/website_data.xml',
        'data/ir_sequence_data.xml',

        # Agrega Vista de Portal para Nuevos Contactos

        # Vistas
        'views/product_product_views.xml',
        'views/sale_order_views.xml',
        'views/appointment_type_views.xml',
        'views/calendar_event_views.xml',
        'views/hotel_appointment_menuitem.xml',

        # Portal / Website
        'views/add_contact_portal_template.xml',
        'views/add_contact_portal_address_tabs.xml',
        'views/hotel_appointment_portal_templates.xml',
        'views/hotel_appointment_website_templates.xml',

        'wizard/sale_order_anglers_views.xml',

    ],
    'assets': {
        'web.assets_backend': [],
        'web.assets_frontend': [
            'stone_appointment/static/src/js/stone_appointment.js',
            'stone_appointment/static/src/js/stone_appointment_select.js',
            'stone_appointment/static/src/css/stone_appointment_select.css',
            'stone_appointment/static/src/css/stone_appointment_form.css',
        ],
        'stone_appointment.stone_embed_assets': [
            # TODO this bundle now includes 'assets_common' files directly, but
            # most of these files are useless in this context, clean this up.
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/lib/select2/select2.css',
            'web/static/lib/select2-bootstrap-css/select2-bootstrap.css',
        ],
    },       
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

# 'stone_appointment/static/lib/select2/*',
# 'stone_appointment/static/src/js/stone_appointment_select2.js',