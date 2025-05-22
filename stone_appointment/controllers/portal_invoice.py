# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import pytz
from collections import OrderedDict
from odoo import http, _
from odoo.http import request
from odoo import _, api, Command, fields, models, SUPERUSER_ID
from odoo.osv.expression import AND, OR
from odoo.addons.account.controllers.portal import PortalAccount
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.resource.models.utils import Intervals, timezone_datetime

class CustomPortalAccount(PortalAccount):


    def _get_portal_invoice_domain(self, m_type=None):
        if m_type in ['in', 'out']:
            move_type = [m_type+move for move in ('_invoice', '_refund', '_receipt')]
        else:
            move_type = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
        return [('state', 'not in', ('cancel', 'draft')), ('move_type', 'in', move_type)]

    def _get_invoice_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('all', 'name'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('all', 'startdate'):
            search_domain = OR([search_domain, [("line_ids.sale_line_ids.order_id.stn_date_start", ">=", search)] ])
        if search_in in ('all', 'angler'):
            search_domain = OR([search_domain, [("line_ids.sale_line_ids.order_id.angler_line.guest_ids", "ilike", search)]])
        return search_domain

    @http.route([
        '/my/invoices', 
        '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', salesperson=None, datetime_filter=None, url="/my/invoices", **kw):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['account.move']
        domain = self._get_portal_invoice_domain()

        searchbar_sortings = self._get_account_searchbar_sortings()
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_inputs = {
            'all': {'label': _('Search in All'), 'input': 'all'},
            'name': {'label': _('Search in Name'), 'input': 'name'},
            'angler': {'label': _('Search in Anglers'), 'input': 'angler'},
        }

        searchbar_groupby = {}
        invoice_count = AccountInvoice.search_count(domain)
        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby, 'filterby': filterby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )        

        searchbar_filters = self._get_account_searchbar_filters()
        if not filterby:
            filterby = 'all'
        domain = AND([domain, searchbar_filters[filterby]['domain']])
        if search and search_in:
            domain = AND([domain, self._get_invoice_search_domain(search_in, search)])

        if datetime_filter:
            user_tz = request.env.user.tz or 'UTC'
            local_tz = pytz.timezone(user_tz)
            local_dt = datetime.strptime(datetime_filter, '%m/%d/%Y %H:%M:%S')
            local_dt = local_tz.localize(local_dt)
            utc_dt = local_dt.astimezone(pytz.UTC)
            utc_dt_str = utc_dt.strftime('%Y-%m-%d %H:%M:%S')
            domain = AND([domain, self._get_invoice_search_domain("startdate", utc_dt_str)])

        session_tz = request.session.get('timezone')
        invoices = AccountInvoice.with_context(tz=session_tz).search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        grouped_invoices = False

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'grouped_invoices': grouped_invoices,
            'page_name': 'invoice',
            'pager': pager,
            'default_url': '/my/invoices',
            'searchbar_sortings': searchbar_sortings,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'filterby': filterby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),

            'search_datetime': True,
            'datetime_filter': datetime_filter
        })
        return request.render("account.portal_my_invoices", values)


    """
    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', salesperson=None, **kw):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['account.move']

        # Definir los filtros de búsqueda para portal_searchbar
        searchbar_inputs = {
            'all': {'input': 'all', 'label': 'Search in All', 'domain': []},
            'number': {'input': 'number', 'label': 'Invoice Number', 'domain': [('name', 'ilike', search)]},
            'salesperson': {'input': 'salesperson', 'label': 'Salesperson', 'domain': [('user_id.name', 'ilike', search)]},
        }

        # Construir el dominio base
        domain = [('move_type', 'in', ('out_invoice', 'out_refund')), ('state', 'not in', ('draft', 'cancel'))]

        # Aplicar el filtro de búsqueda si existe
        if search and search_in in searchbar_inputs:
            domain += searchbar_inputs[search_in]['domain']

        # Lógica de ordenación y paginación
        sortby = sortby or 'date'
        order = 'date desc' if sortby == 'date' else 'name desc'
        
        invoice_count = AccountInvoice.search_count(domain)
        pager = request.website.pager(
            url="/my/invoices",
            total=invoice_count,
            page=page,
            step=10,
        )

        invoices = AccountInvoice.search(domain, order=order, limit=10, offset=pager['offset'])
        values.update({
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'default_url': '/my/invoices',
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': searchbar_inputs,
        })
        
        return request.render("account.portal_my_invoices", values)
    """
