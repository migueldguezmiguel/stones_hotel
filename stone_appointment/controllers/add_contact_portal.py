# -*- coding: utf-8 -*-

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request, route

class CustomerPortal(CustomerPortal):

    def _prepare_prsit_add_contact_address(self):
        partner = request.env.user.partner_id
        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])
        types = request.env['res.partner']._fields['type'].selection
        return {
            'partner': partner,
            'countries': countries,
            'states': states,
            'types': [('other', 'Other Address')]
        }

    def _prepare_prsit_submit_contact_address(self, kwargs):
        return {
            'type': kwargs.get('type'),
            'name': kwargs.get('name'),
            'email': kwargs.get('email'),
            'mobile': kwargs.get('mobile'),
            'phone': kwargs.get('phone'),
            'street': kwargs.get('street'),
            'city': kwargs.get('city'),
            'zip': kwargs.get('zip'),
            'state_id': int(kwargs.get('state_id')),
            'country_id': int(kwargs.get('country_id')),
            'parent_id': request.env.user.partner_id.id,
        }

    @route(['/my/<string:partner>/contact/add', '/my/contact/add'], type='http', auth='user', website=True)
    def add_prsit_contact_address(self, **kwargs):
        values = self._prepare_prsit_add_contact_address()
        if kwargs.get('type'):
            values.update({'address_type': kwargs.get('type')})
        return request.render("stone_appointment.add_contact_my_details", values)

    @route(['/my/<string:address_type>/submit'], type='http', auth='user', website=True)
    def submit_prsit_contact(self, **kwargs):
        partner = request.env.user.partner_id
        if kwargs and request.httprequest.method == 'POST':
            child_data_vals = self._prepare_prsit_submit_contact_address(kwargs)
            request.env['res.partner'].sudo().create(
                child_data_vals
            )
        return request.redirect('/my/account')

