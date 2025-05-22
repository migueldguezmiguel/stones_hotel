# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from operator import itemgetter
import pytz

from odoo import http, _
from odoo.http import request
from odoo.osv.expression import AND, OR
from odoo.tools import groupby as groupbyelem

from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.resource.models.utils import Intervals, timezone_datetime

class ReservationPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'reservation_count' in counters:
            domain = self._get_portal_default_domain()
            values['reservation_count'] = request.env['calendar.event'].search_count(domain)
        return values

    def _get_portal_default_domain(self):
        my_user = request.env.user
        return [
            ('user_id', '!=', my_user.id),
            ('partner_ids', 'in', my_user.partner_id.ids),
            ('appointment_type_id', '!=', False),
        ]

    def _get_reservation_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('all', 'name'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('all', 'quotation'):
            search_domain = OR([search_domain, [('sale_id', 'ilike', search)]])
        if search_in in ('all', 'field'):
            search_domain = OR([search_domain, [('sale_id.recurso_id', 'ilike', search)]])
        if search_in in ('all', 'status'):
            search_domain = OR([search_domain, [('sale_id.state', 'ilike', search)]])
        if search_in in ('all', 'angler'):
            search_domain = OR([search_domain, [('sale_id.angler_line.guest_ids', 'ilike', search)]])
        if search_in in ('all', 'description'):
            search_domain = OR([search_domain, [('description', 'ilike', search)]])
        if search_in in ('all', 'startdate'):
            search_domain = OR([search_domain, [("sale_id.stn_date_start", ">=", search)] ])
        return search_domain

    def _reservation_get_groupby_mapping(self):
        return {
            'responsible': 'user_id',
            'field': 'recurso_id',
            'status': 'sale_state',
        }

    @http.route(['/my/reservations',
                 '/my/reservations/page/<int:page>',
                ], type='http', auth='user', website=True)
    def portal_my_reservation(self, page=1, sortby=None, filterby=None, search=None, search_in='all', groupby='none', datetime_filter=None,  **kwargs):
        values = self._prepare_portal_layout_values()
        Event = request.env['calendar.event'].sudo()
        domain = self._get_portal_default_domain()

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'start'},
            'Quotation': {'label': _('Quotation'), 'order': 'sale_id'},
            'Field': {'label': _('Field'), 'order': 'recurso_id'},
            'Status': {'label': _('Status'), 'order': 'sale_state'},
        }

        searchbar_inputs = {
            'all': {'label': _('Search in All'), 'input': 'all'},
            'quotation': {'label': _('Search in Quotation'), 'input': 'quotation'},
            'field': {'label': _('Search in Field'), 'input': 'field'},
            'status': {'label': _('Search in Status'), 'input': 'status'},
            'angler': {'label': _('Search in Anglers'), 'input': 'angler'}
        }

        # 'responsible': {'label': _('Responsible'), 'input': 'responsible'},
        searchbar_groupby = {
            'none': {'label': _('None'), 'input': 'none'},
            'field': {'label': _('Field'), 'input': 'field'},
        }

        # 'upcoming': {'label': _("Upcoming"), 'domain': [('start', '>=', datetime.today())]},
        # 'past': {'label': _("Past"), 'domain': [('start', '<', datetime.today())]},
        # 'all': {'label': _("All"), 'domain': []},
        searchbar_filters = {}

        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']
        groupby_mapping = self._reservation_get_groupby_mapping()
        groupby_field = groupby_mapping.get(groupby, None)
        if groupby_field is not None and groupby_field not in Event._fields:
            raise ValueError(_("The field '%s' does not exist in the targeted model", groupby_field))
        order = '%s, %s' % (groupby_field, sort_order) if groupby_field else sort_order

        # if not filterby:
        #     filterby = 'all'
        # domain = AND([domain, searchbar_filters[filterby]['domain']])

        if search and search_in:
            domain = AND([domain, self._get_reservation_search_domain(search_in, search)])

        if datetime_filter:
            user_tz = request.env.user.tz or 'UTC'
            local_tz = pytz.timezone(user_tz)
            local_dt = datetime.strptime(datetime_filter, '%m/%d/%Y %H:%M:%S')
            local_dt = local_tz.localize(local_dt)
            utc_dt = local_dt.astimezone(pytz.UTC)
            utc_dt_str = utc_dt.strftime('%Y-%m-%d %H:%M:%S')
            domain = AND([domain, self._get_reservation_search_domain("startdate", utc_dt_str)])


        reservation_count = Event.search_count(domain)
        pager = portal_pager(
            url="/my/reservations",
            url_args={'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby, 'filterby': filterby},
            total=reservation_count,
            page=page,
            step=self._items_per_page
        )
        reservations = Event.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        grouped_reservations = False
        # If not False, this will contain a list of tuples (record of groupby, recordset of events):
        # [(res.users(2), calendar.event(1, 2)), (...), ...]
        if groupby_field:
            grouped_reservations = [(g, Event.concat(*events)) for g, events in groupbyelem(reservations, itemgetter(groupby_field))]        

        values.update({
            'reservations': reservations,
            'grouped_reservations': grouped_reservations,
            'page_name': 'reservation',
            'pager': pager,
            'default_url': '/my/reservations',
            'searchbar_sortings': searchbar_sortings,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
            'groupby': groupby,
            'filterby': filterby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_filters': searchbar_filters,
            'search_datetime': True,
            'datetime_filter': datetime_filter
        })
        return request.render("stone_appointment.portal_my_reservation", values)


