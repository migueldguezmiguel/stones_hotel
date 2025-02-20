# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import calendar as cal
import random
import pytz

from datetime import datetime, timedelta, time
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from babel.dates import format_datetime, format_time

from odoo.http import request
from odoo import fields, models

from odoo.tools.misc import babel_locale_parse, get_lang
from odoo.addons.base.models.res_partner import _tz_get

class AppointmentType(models.Model):
    _inherit = "appointment.type"

    product_tmpl_id = fields.Many2one('product.template', string='Product')
    additional_fees_ids = fields.Many2many(
        comodel_name='sale.additional.fees',
        string="Additional Fees", readonly=False)

    def get_datetime_timezone_appointment_type(self, date_dt, appointment_type):
        session_tz = request.session.get('timezone', appointment_type.appointment_tz)
        tz_info = pytz.timezone(session_tz)
        date_dt_utc = tz_info.localize(fields.Datetime.from_string(date_dt)).astimezone(pytz.utc)
        return date_dt_utc

    def get_localtime_timezone_appointment_type(self, date_dt):
        appt_tz = pytz.timezone(self.appointment_tz)
        ref_tz_apt_type = date_dt.astimezone(appt_tz)
        return ref_tz_apt_type.strftime("%Y-%m-%d %H:%M:%S")

    def get_recursos_disponibles(self, start_dt, end_dt, recurso_id):
        AnglerLineModel = self.env['sale.line.angler'].sudo()
        BookingLinesModel = self.env['appointment.booking.line'].sudo()
        ResourceModel = request.env['appointment.resource'].sudo()
        related_resources = recurso_id.resource_ids
        events = BookingLinesModel.search([
            ('appointment_resource_id', 'in', related_resources.ids),
            ('event_start', '>=', start_dt),
            ('event_stop', '<=', end_dt),
        ])
        resources = events.mapped("appointment_resource_id")
        habitaciones = related_resources.filtered(lambda x: x.id not in resources.ids)
        resource_ids = AnglerLineModel.search([
            ('stn_date_start', '>=', start_dt),
            ('stn_date_stop', '<=', end_dt),
        ]).mapped("resource_ids")
        habitaciones = habitaciones.filtered(lambda x: x.id not in resource_ids.ids)
        return habitaciones

    def get_guias_disponibles(self, start_dt, end_dt, appointment_type):
        PartnerModel = self.env["res.partner"].sudo()
        EventModel = self.env['calendar.event'].sudo()
        AnglerLineModel = self.env['sale.line.angler'].sudo()

        partners = PartnerModel
        related_partners = self.staff_user_ids.mapped("partner_id")
        all_events = self.env['calendar.event'].search(
            ['&',
             ('partner_ids', 'in', related_partners.ids),
             '&', '&',
             ('show_as', '=', 'busy'),
             ('stop', '>=', start_dt),
             ('start', '<=', end_dt),
            ],
            order='start asc',
        )
        partners |= all_events.mapped("partner_ids")
        guias_ids = related_partners.filtered(lambda x: x.id not in partners.ids)
        angler_ids = AnglerLineModel.search([
            ('stn_date_start', '>=', start_dt),
            ('stn_date_stop', '<=', end_dt),
        ]).mapped("guides_ids")
        guias_ids = guias_ids.filtered(lambda x: x.id not in angler_ids.ids)
        return guias_ids

    def action_create_event_rrule(self):
        timezone = self.appointment_tz
        requested_tz = pytz.timezone(self.appointment_tz)
        reference_date = datetime.utcnow()
        appointment_duration_days = self.max_schedule_days
        slot_datys = [int(slot.weekday)  for slot in self.slot_ids]
        first_day = requested_tz.fromutc(reference_date + relativedelta(hours=self.min_schedule_hours))
        last_day = requested_tz.fromutc(reference_date + relativedelta(days=appointment_duration_days))

        slots = self._slots_generate(
            first_day.astimezone(pytz.utc),
            last_day.astimezone(pytz.utc),
            self.appointment_tz,
            reference_date=reference_date
        )
        today = requested_tz.fromutc(reference_date)
        start = slots[0][self.appointment_tz][0] if slots else today
        locale = babel_locale_parse(get_lang(self.env).code)
        month_dates_calendar = cal.Calendar(locale.first_week_day).monthdatescalendar
        months = []
        nb_slots_previous_months = 0
        nb_slots_next_months = 0
        while (start.year, start.month) <= (last_day.year, last_day.month):
            has_availabilities = False
            dates = month_dates_calendar(start.year, start.month)
            for week_index, week in enumerate(dates):
                for day_index, day in enumerate(week):
                    if day.isoweekday() not in slot_datys:
                        continue
                    mute_cls = weekend_cls = today_cls = None
                    today_slots = []
                    if day.weekday() in (locale.weekend_start, locale.weekend_end):
                        weekend_cls = 'o_weekend bg-light'
                    if day == today.date() and day.month == today.month:
                        today_cls = 'o_today'
                    if day.month != start.month:
                        mute_cls = 'text-muted o_mute_day'
                    else:
                        # slots are ordered, so check all unprocessed slots from until > day
                        while slots and (slots[0][timezone][0].date() <= day):
                            slots.pop(0)
                    today_slots = sorted(today_slots, key=lambda d: d['datetime'])
                    dates[week_index][day_index] = {
                        'day': day,
                    }
                    has_availabilities = has_availabilities or bool(today_slots)
            months.append({
                'id': len(months),
                'month': format_datetime(start, 'MMMM Y', locale=get_lang(self.env).code),
                'weeks': dates,
            })
            start = start + relativedelta(months=1)

        slot_datas = []
        for month in months:
            slot_tmp = {
                "id": month.get("id"),
                "month": month.get("month") or "",
                "weeks": []
            }
            for weeks in month.get("weeks") or []:
                for week in weeks:
                    if isinstance(week, dict):
                        slot_tmp["weeks"].append( week.get('day') )
            slot_datas.append(slot_tmp)
        return slot_datas

