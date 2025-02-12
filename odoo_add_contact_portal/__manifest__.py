# -*- coding: utf-8 -*-
{
    'name': 'Odoo Add Contact Portal',
    'summary': "Odoo Add contact portal",
    'description': """
        Odoo Add contact portal
        Odoo Add Sub contact portal
        Add Invoicing Address from portal
        Add Shipping Address From Portal
        Add Other Address From Portal
        View Sub Contacts on Portal View""",
    'author': "ProsIT",
    'website': 'prosit.contactus@gmail.com',
    'license': 'OPL-1',
    'price': '45.0',
    'currency': 'USD',
    'category': 'Portal/Contacts',
    'version': '1.0.0',
    'images': [
        'static/description/module_image.jpg',
    ],
    'depends': [
        'portal',
        'website',
    ],
    'data': [
        'views/address_type_tabs.xml',
        'views/add_contact_portal_templates.xml',
    ],
    'installable': True,
    'application': True

}
