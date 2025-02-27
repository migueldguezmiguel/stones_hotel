# -*- coding: utf-8 -*-

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request, route

class CustomerPortal(CustomerPortal):

    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        response = super(CustomerPortal, self).account(redirect=redirect, **post)
        values = response.qcontext
        search = post.get('search', False)


        domain = [('parent_id', '=', request.env.user.partner_id.id), ('type', '=', 'other')]
        if search:
            domain.append(('name', 'ilike', search))  # Búsqueda por nombre
        
        contacts = request.env['res.partner'].sudo().search(domain)

        values.update({
            'contacts': contacts,
            'search': search or '',
        })

        response = request.render("portal.portal_my_details", values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response


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

    @route('/my/contacts/edit/<int:contact_id>', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def edit_contact(self, contact_id, **kwargs):
        contact = request.env['res.partner'].sudo().browse(contact_id)
        if not contact.exists() or contact.parent_id != request.env.user.partner_id:
            return request.redirect('/my/account')
        
        if request.httprequest.method == 'POST':
            values = {
                'name': kwargs.get('name'),
                'email': kwargs.get('email'),
                'mobile': kwargs.get('mobile'),
                'phone': kwargs.get('phone'),
                'street': kwargs.get('street'),
                'city': kwargs.get('city'),
                'zip': kwargs.get('zip'),
                'state_id': int(kwargs.get('state_id')) if kwargs.get('state_id') else False,
                'country_id': int(kwargs.get('country_id')) if kwargs.get('country_id') else False,
            }
            contact.write(values)
            return request.redirect('/my/account')
        
        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])
        return request.render('stone_appointment.edit_contact_template', {
            'contact': contact,
            'countries': countries,
            'states': states,
        })


    @route('/my/contacts/delete/<int:contact_id>', type='http', auth='user', website=True)
    def delete_contact(self, contact_id):
        contact = request.env['res.partner'].sudo().browse(contact_id)
        if contact.exists() and contact.parent_id == request.env.user.partner_id:
            contact.unlink()
        return request.redirect('/my/account')

