# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pytz
import re

import urllib.parse
from datetime import datetime, timedelta, time
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from babel.dates import format_date

from werkzeug.exceptions import Forbidden, NotFound
from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.appointment.controllers.appointment import AppointmentController
from odoo.addons.appointment.controllers.calendar import AppointmentCalendarController

from odoo import fields, _
from odoo import http
from odoo.http import request, route
from odoo.tools.misc import babel_locale_parse

def _formated_weekdays(locale):
    """ Return the weekdays' name for the current locale
        from Mon to Sun.
        :param locale: locale
    """
    formated_days = [
        format_date(date(2021, 3, day), 'EEE', locale=locale)
        for day in range(1, 8)
    ]
    # Get the first weekday based on the lang used on the website
    first_weekday_index = babel_locale_parse(locale).first_week_day
    # Reorder the list of days to match with the first weekday
    formated_days = list(formated_days[first_weekday_index:] + formated_days)[:7]
    return formated_days

class AppointmentCalendarControllerCustom(AppointmentCalendarController):

    @route(['/calendar/cancel/<string:access_token>',
            '/calendar/<string:access_token>/cancel',
           ], type='http', auth="public", website=True)
    def appointment_cancel(self, access_token, partner_id, **kwargs):
        """
            Route to cancel an appointment event, this route is linked to a button in the validation page
        """
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        appointment_type = event.appointment_type_id
        appointment_invite = event.appointment_invite_id
        if not event:
            return request.not_found()
        if fields.Datetime.from_string(event.allday and event.start_date or event.start) < datetime.now() + timedelta(hours=event.appointment_type_id.min_cancellation_hours):
            return request.redirect(f'/calendar/view/{access_token}?state=no-cancel&partner_id={partner_id}')
        event.with_context(mail_notify_author=True).sudo().action_cancel_meeting([int(partner_id)])
        if appointment_invite:
            redirect_url = appointment_invite.redirect_url + '&state=cancel'
        else:
            if request.session.stn_sale_id:
                redirect_url = "/web/reservation"
                request.session["stn_sale_id"] = False
                request.session["stn_indx_data"] = {}
            else:
                redirect_url = "/web/reservation"
                request.session["stn_sale_id"] = False
                request.session["stn_indx_data"] = {}
        return request.redirect(redirect_url)


class AppointmentControllerWebsite(http.Controller):

    @route(['/web/reservation'], type='http', auth="user", website=True, csrf=False)
    def website_reservation_index(self, package_id="", recurso_id="", date_start="", date_stop="", **kwargs):
        # request.session["stn_sale_id"] = False 
        SaleOrderModel = request.env['sale.order'].sudo()
        AttributeModel = request.env['product.attribute'].sudo()
        RecursosModel = request.env['sale.resources'].sudo()
        TypeModel = request.env['appointment.type'].sudo()

        sale_id = SaleOrderModel.get_saleorder_portal_reservation()

        internal_note = ""
        if request.session.stn_indx_data:
            stn_data = request.session["stn_indx_data"]
            internal_note = stn_data.get("internal_note")
            package_id = stn_data.get("package_id")
            recurso_id = stn_data.get("recurso_id")
            date_start = stn_data.get("date_start")
            date_stop = stn_data.get("date_stop")

        type_ids = TypeModel.search([('product_tmpl_id', '!=', False)])
        packages = type_ids.mapped('product_tmpl_id')
        package_title = ""
        if package_id:
            package = packages.filtered(lambda x: x.id == int(package_id) )
            package_title = package and package.name or ''

        recurso_title = ""
        recursos = [ {"id": "%s"%rec.id, "name": rec.name } for rec in RecursosModel.search([]) ]
        if recurso_id:
            recurso_title = next(filter(lambda recurso: recurso['id'] == recurso_id, recursos))
            recurso_title = recurso_title.get("name") or ""
        if not date_start:
            date_start = datetime.today().date()
        if not date_stop:
            date_stop = datetime.today().date()

        slots_rules = []
        params = {
            "packages": packages,
            "package_id": int(package_id or 0),
            "package_title": package_title,
            "recursos": recursos,
            "recurso_id": recurso_id,
            "recurso_title": recurso_title,
            "date_start": date_start,
            "date_stop": date_stop,
            "allday": True,
            "slots_rules": slots_rules,
            "internal_note": internal_note,
            **kwargs
        }
        return request.render(
            "stone_appointment.reservations_web_index", 
            params
        )

    @route(['/web/reservation/extra'], type='http', auth="user", website=True)
    def website_reservation_extra(self, package_id="", recurso_id="", date_start="", date_stop="", **kwargs):
        AppointmentModel = request.env['appointment.type'].sudo()
        CalendarModel = request.env['calendar.event'].sudo()
        PartnerModel = request.env['res.partner'].sudo()
        SaleOrderModel = request.env['sale.order'].sudo()
        SaleResourceModel = request.env['sale.resources'].sudo()
        TemplateModel = request.env['product.template'].sudo()
        AttributeModel = request.env['product.attribute'].sudo()

        product_tmpl_id = TemplateModel.search([('id', '=', package_id)])
        recurso_id = SaleResourceModel.search([('id', '=', recurso_id)])
        appointment_id = AppointmentModel.search([('product_tmpl_id', '=', product_tmpl_id.id)])

        if isinstance(date_start, str):
            date_start = datetime.strptime(date_start, '%Y-%m-%d')
        date_stop = date_start + relativedelta(days=6)

        # Guias
        guias = appointment_id.get_guias_disponibles(date_start, date_stop)
        habitaciones = appointment_id.get_recursos_disponibles(recurso_id, date_start, date_stop)

        # Opciones
        option_ids = []
        for tmp in product_tmpl_id:
            for line in tmp.attribute_line_ids:
                option_ids = AttributeModel.get_ws_product_attribute_value(attribute_id=line.attribute_id)

        sale_id = SaleOrderModel.get_saleorder_portal_reservation()

        # Clientes
        partner = request.env.user.partner_id
        contactos = PartnerModel.search([('parent_id', '=', partner.id)])

        internal_note = ""
        if request.session.stn_indx_data:
            internal_note = request.session["stn_indx_data"].get("internal_note")

        params = {
            "appointment_id": appointment_id,
            "product_tmpl_id": product_tmpl_id,

            "recurso": recurso_id,
            "guias": guias,
            "total_guias": len(guias.ids),
            "habitaciones": habitaciones,
            "total_habitaciones": len(habitaciones),

            "contactos": contactos,
            "package_id": package_id,
            "recurso_id": recurso_id,
            "date_start": date_start,
            "date_stop": date_stop,
            "option_ids": option_ids,
            "stn_sale_id": sale_id,
            "internal_note": internal_note,

            **kwargs
        }
        return request.render(
            "stone_appointment.reservations_web_extra", 
            params, 
            headers={'Cache-Control': 'no-store'}
        )

    @route(['/web/reservation/viewcomfirm'], type='http', auth="user", website=True, sitemap=True)
    def website_reservation_viewcomfirm(self, package_id="", recurso_id="", date_start="", date_stop="", **kwargs):
        SaleOrderModel = request.env['sale.order'].sudo()
        sale_id = SaleOrderModel.get_saleorder_portal_reservation()
        if sale_id:
            url_request = '/calendar/view/%s?partner_id=%s'%( sale_id.event_id.access_token, request.env.user.partner_id.id)
            request.session["stn_sale_id"] = False
            request.session["stn_indx_data"] = {}
            return request.redirect(url_request)

        params = {
            "package_id": package_id,
            "recurso_id": recurso_id,
            "date_start": date_start,
            "date_stop": date_stop,
            "stn_sale_id": sale_id,
        }
        return request.render(
            "stone_appointment.reservations_web_comfirm", 
            params, 
            headers={'Cache-Control': 'no-store'}
        )

    # Realiza calculos JSON
    @http.route(['/web/reservation/cancel'], type='json', auth='user', website=True)
    def web_reservation_cancel(self, **kwargs):
        SaleOrderModel = request.env['sale.order'].sudo()
        sale_id = SaleOrderModel.get_saleorder_portal_reservation()
        if sale_id.event_id:
            redirect_url = '/calendar/view/%s?partner_id=%s'%( sale_id.event_id.access_token, request.env.user.partner_id.id)
            return {"redirect_url": redirect_url}
        elif sale_id:
            sale_id.action_cancel()
            return {"redirect_url": "/web/reservation"}
        else:
            return {"redirect_url": "/web/reservation"}
        return {}


    @http.route('/stn_reservation/extra', type='json', auth='user', methods=['POST'])
    def stn_reservation_extra(self, package_id="", recurso_id="", date_start="", date_stop="", internal_note="", **kwargs):
        params = {
            "package_id": package_id,
            "recurso_id": recurso_id,
            "date_start": date_start,
            "date_stop": date_stop,
        }
        datas = urllib.parse.urlencode(params)

        params_tmp = params.copy()
        params_tmp.update({
            "internal_note": internal_note
        })
        if not request.session.stn_indx_data:
            request.session["stn_indx_data"] = params_tmp
        if request.session.stn_indx_data and not request.session.stn_sale_id:
            request.session["stn_indx_data"] = params_tmp
        return {
            'force_refresh': True,
            'redirect_url': '/web/reservation/extra?' + datas,
        }

    @http.route(['/web/reservation/sale/validate'], type='json', auth='user', website=True)
    def web_reservation_sale_lines(self, **kwargs):
        SaleOrderModel = request.env['sale.order'].sudo()
        SaleOrderModel.action_create_sale_order_from_reservations(datas=kwargs)
        return {}

    @http.route(['/web/reservation/sale/lines'], type='json', auth='user', website=True)
    def web_reservation_sale_lines(self, **kwargs):
        SaleOrderModel = request.env['sale.order'].sudo()
        res = SaleOrderModel.action_create_sale_order_from_reservations(datas=kwargs)
        return res

    @http.route(['/web/reservation/comfirm'], type='json', auth='user', website=True)
    def web_reservation_comfirm(self, **kwargs):
        SaleOrderModel = request.env['sale.order'].sudo()
        sale_id = SaleOrderModel.get_saleorder_portal_reservation()
        if sale_id:
            sale_id.action_create_website_event(datas=kwargs)
        return {}

    @http.route('/web/reservation/slots', type='json', auth='user', methods=['POST'])
    def web_reservation_slots(self, package_id=0, **kwargs):
        if not package_id or int(package_id) <= 0:
            return []
        datas = []
        AppointmentModel = request.env['appointment.type'].sudo()
        appointment_id = AppointmentModel.search([('product_tmpl_id', '=', int(package_id))])
        slots_rules = appointment_id.action_create_event_rrule()
        for slot in slots_rules:
            for week in slot.get("weeks"):
                datas.append({
                    "id": week,
                    "text": week,
                    "create": True
                })
        return datas

