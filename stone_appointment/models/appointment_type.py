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

    def get_recursos_disponibles(self, recurso_id, start_dt, end_dt):
        AnglerLineModel = self.env['sale.line.angler'].sudo()
        BookingLinesModel = self.env['appointment.booking.line'].sudo()
        ResourceModel = request.env['appointment.resource'].sudo()

        related_resources = recurso_id.resource_ids
        resources = ResourceModel
        for resource in related_resources:
            events = BookingLinesModel.search([
                ('appointment_resource_id', '=', resource.id),
                ('event_start', '<', datetime.combine(start_dt, time.min)),
                ('event_stop', '>', datetime.combine(end_dt, time.max)),
            ])
            resources |= events.mapped("appointment_resource_id")
        habitaciones = related_resources.filtered(lambda x: x.id not in resources.ids)

        resource_ids = AnglerLineModel.search([
            ('stn_date_stop', '>=', start_dt),
            ('stn_date_start', '<=', end_dt),
        ]).mapped("resource_ids")
        habitaciones = habitaciones.filtered(lambda x: x.id not in resource_ids.ids)
        return habitaciones

    def get_guias_disponibles(self, start_dt, end_dt):
        PartnerModel = self.env["res.partner"].sudo()
        EventModel = self.env['calendar.event'].sudo()
        AnglerLineModel = self.env['sale.line.angler'].sudo()

        related_partners = self.staff_user_ids.mapped("partner_id")
        partners = PartnerModel
        for partner in related_partners:
            events = EventModel.search(['&',
                ('partner_ids', 'in', partner.ids),
                '&', '&',
                ('show_as', '=', 'busy'),
                ('stop', '>=', datetime.combine(start_dt, time.min)),
                ('start', '<=', datetime.combine(end_dt, time.max)),
            ], order='start asc')
            partners |= events.mapped("partner_ids")
        guias_ids = related_partners.filtered(lambda x: x.id not in partners.ids)

        angler_ids = AnglerLineModel.search([
            ('stn_date_stop', '>=', start_dt),
            ('stn_date_start', '<=', end_dt),
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

"""
[
    {
        "id": 0,
        "month": "February 2025",
        "weeks": [
            datetime.date(2025, 1, 27),
            datetime.date(2025, 2, 1),
            datetime.date(2025, 2, 3),
            datetime.date(2025, 2, 8),
            datetime.date(2025, 2, 10),
            datetime.date(2025, 2, 15),
            datetime.date(2025, 2, 17),
            datetime.date(2025, 2, 22),
            datetime.date(2025, 2, 24),
            datetime.date(2025, 3, 1),
        ],
    },
    {
        "id": 1,
        "month": "March 2025",
        "weeks": [
            datetime.date(2025, 2, 24),
            datetime.date(2025, 3, 1),
            datetime.date(2025, 3, 3),
            datetime.date(2025, 3, 8),
            datetime.date(2025, 3, 10),
            datetime.date(2025, 3, 15),
            datetime.date(2025, 3, 17),
            datetime.date(2025, 3, 22),
            datetime.date(2025, 3, 24),
            datetime.date(2025, 3, 29),
            datetime.date(2025, 3, 31),
            datetime.date(2025, 4, 5),
        ],
    },
    {
        "id": 2,
        "month": "April 2025",
        "weeks": [
            datetime.date(2025, 3, 31),
            datetime.date(2025, 4, 5),
            datetime.date(2025, 4, 7),
            datetime.date(2025, 4, 12),
            datetime.date(2025, 4, 14),
            datetime.date(2025, 4, 19),
            datetime.date(2025, 4, 21),
            datetime.date(2025, 4, 26),
            datetime.date(2025, 4, 28),
            datetime.date(2025, 5, 3),
        ],
    },
    {
        "id": 3,
        "month": "May 2025",
        "weeks": [
            datetime.date(2025, 4, 28),
            datetime.date(2025, 5, 3),
            datetime.date(2025, 5, 5),
            datetime.date(2025, 5, 10),
            datetime.date(2025, 5, 12),
            datetime.date(2025, 5, 17),
            datetime.date(2025, 5, 19),
            datetime.date(2025, 5, 24),
            datetime.date(2025, 5, 26),
            datetime.date(2025, 5, 31),
        ],
    },
    {
        "id": 4,
        "month": "June 2025",
        "weeks": [
            datetime.date(2025, 6, 2),
            datetime.date(2025, 6, 7),
            datetime.date(2025, 6, 9),
            datetime.date(2025, 6, 14),
            datetime.date(2025, 6, 16),
            datetime.date(2025, 6, 21),
            datetime.date(2025, 6, 23),
            datetime.date(2025, 6, 28),
            datetime.date(2025, 6, 30),
            datetime.date(2025, 7, 5),
        ],
    },
    {
        "id": 5,
        "month": "July 2025",
        "weeks": [
            datetime.date(2025, 6, 30),
            datetime.date(2025, 7, 5),
            datetime.date(2025, 7, 7),
            datetime.date(2025, 7, 12),
            datetime.date(2025, 7, 14),
            datetime.date(2025, 7, 19),
            datetime.date(2025, 7, 21),
            datetime.date(2025, 7, 26),
            datetime.date(2025, 7, 28),
            datetime.date(2025, 8, 2),
        ],
    },
    {
        "id": 6,
        "month": "August 2025",
        "weeks": [
            datetime.date(2025, 7, 28),
            datetime.date(2025, 8, 2),
            datetime.date(2025, 8, 4),
            datetime.date(2025, 8, 9),
            datetime.date(2025, 8, 11),
            datetime.date(2025, 8, 16),
            datetime.date(2025, 8, 18),
            datetime.date(2025, 8, 23),
            datetime.date(2025, 8, 25),
            datetime.date(2025, 8, 30),
            datetime.date(2025, 9, 1),
            datetime.date(2025, 9, 6),
        ],
    },
    {
        "id": 7,
        "month": "September 2025",
        "weeks": [
            datetime.date(2025, 9, 1),
            datetime.date(2025, 9, 6),
            datetime.date(2025, 9, 8),
            datetime.date(2025, 9, 13),
            datetime.date(2025, 9, 15),
            datetime.date(2025, 9, 20),
            datetime.date(2025, 9, 22),
            datetime.date(2025, 9, 27),
            datetime.date(2025, 9, 29),
            datetime.date(2025, 10, 4),
        ],
    },
    {
        "id": 8,
        "month": "October 2025",
        "weeks": [
            datetime.date(2025, 9, 29),
            datetime.date(2025, 10, 4),
            datetime.date(2025, 10, 6),
            datetime.date(2025, 10, 11),
            datetime.date(2025, 10, 13),
            datetime.date(2025, 10, 18),
            datetime.date(2025, 10, 20),
            datetime.date(2025, 10, 25),
            datetime.date(2025, 10, 27),
            datetime.date(2025, 11, 1),
        ],
    },
    {
        "id": 9,
        "month": "November 2025",
        "weeks": [
            datetime.date(2025, 10, 27),
            datetime.date(2025, 11, 1),
            datetime.date(2025, 11, 3),
            datetime.date(2025, 11, 8),
            datetime.date(2025, 11, 10),
            datetime.date(2025, 11, 15),
            datetime.date(2025, 11, 17),
            datetime.date(2025, 11, 22),
            datetime.date(2025, 11, 24),
            datetime.date(2025, 11, 29),
            datetime.date(2025, 12, 1),
            datetime.date(2025, 12, 6),
        ],
    },
    {
        "id": 10,
        "month": "December 2025",
        "weeks": [
            datetime.date(2025, 12, 1),
            datetime.date(2025, 12, 6),
            datetime.date(2025, 12, 8),
            datetime.date(2025, 12, 13),
            datetime.date(2025, 12, 15),
            datetime.date(2025, 12, 20),
            datetime.date(2025, 12, 22),
            datetime.date(2025, 12, 27),
            datetime.date(2025, 12, 29),
            datetime.date(2026, 1, 3),
        ],
    },
    {
        "id": 11,
        "month": "January 2026",
        "weeks": [
            datetime.date(2025, 12, 29),
            datetime.date(2026, 1, 3),
            datetime.date(2026, 1, 5),
            datetime.date(2026, 1, 10),
            datetime.date(2026, 1, 12),
            datetime.date(2026, 1, 17),
            datetime.date(2026, 1, 19),
            datetime.date(2026, 1, 24),
            datetime.date(2026, 1, 26),
            datetime.date(2026, 1, 31),
        ],
    },
    {
        "id": 12,
        "month": "February 2026",
        "weeks": [
            datetime.date(2026, 2, 2),
            datetime.date(2026, 2, 7),
            datetime.date(2026, 2, 9),
            datetime.date(2026, 2, 14),
            datetime.date(2026, 2, 16),
            datetime.date(2026, 2, 21),
            datetime.date(2026, 2, 23),
            datetime.date(2026, 2, 28),
        ],
    },
    {
        "id": 13,
        "month": "March 2026",
        "weeks": [
            datetime.date(2026, 3, 2),
            datetime.date(2026, 3, 7),
            datetime.date(2026, 3, 9),
            datetime.date(2026, 3, 14),
            datetime.date(2026, 3, 16),
            datetime.date(2026, 3, 21),
            datetime.date(2026, 3, 23),
            datetime.date(2026, 3, 28),
            datetime.date(2026, 3, 30),
            datetime.date(2026, 4, 4),
        ],
    },
    {
        "id": 14,
        "month": "April 2026",
        "weeks": [
            datetime.date(2026, 3, 30),
            datetime.date(2026, 4, 4),
            datetime.date(2026, 4, 6),
            datetime.date(2026, 4, 11),
            datetime.date(2026, 4, 13),
            datetime.date(2026, 4, 18),
            datetime.date(2026, 4, 20),
            datetime.date(2026, 4, 25),
            datetime.date(2026, 4, 27),
            datetime.date(2026, 5, 2),
        ],
    },
    {
        "id": 15,
        "month": "May 2026",
        "weeks": [
            datetime.date(2026, 4, 27),
            datetime.date(2026, 5, 2),
            datetime.date(2026, 5, 4),
            datetime.date(2026, 5, 9),
            datetime.date(2026, 5, 11),
            datetime.date(2026, 5, 16),
            datetime.date(2026, 5, 18),
            datetime.date(2026, 5, 23),
            datetime.date(2026, 5, 25),
            datetime.date(2026, 5, 30),
            datetime.date(2026, 6, 1),
            datetime.date(2026, 6, 6),
        ],
    },
    {
        "id": 16,
        "month": "June 2026",
        "weeks": [
            datetime.date(2026, 6, 1),
            datetime.date(2026, 6, 6),
            datetime.date(2026, 6, 8),
            datetime.date(2026, 6, 13),
            datetime.date(2026, 6, 15),
            datetime.date(2026, 6, 20),
            datetime.date(2026, 6, 22),
            datetime.date(2026, 6, 27),
            datetime.date(2026, 6, 29),
            datetime.date(2026, 7, 4),
        ],
    },
]

"""