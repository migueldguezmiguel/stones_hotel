# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time
from dateutil import rrule
from odoo import _, api, fields, models

class CalendarEvent(models.Model):
    _inherit = "calendar.event"
    _order = 'start desc, folio desc'

    sale_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order Reference",
        required=False, ondelete='cascade', index=True, copy=False)
    folio = fields.Char(string="Folio", default="/")
    stn_no_personas = fields.Integer("Numero de Personas")
    stn_no_habitaciones = fields.Integer("Numero de Habitaciones")
    stn_no_guias = fields.Integer("Numero de Guias")
    stn_precio_total = fields.Float(string="Amount Total", compute='_compute_stn_precio_total')

    stn_angler_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='calendar_event_anglers_partner_rel',
        column1='event_id',
        column2='angler_id',
        copy=False,
        readonly=False,
    )
    stn_guides_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='calendar_event_anglers_guides_rel',
        column1='event_id',
        column2='guides_id',
        copy=False,
        readonly=False,
    )
    stn_pref_guides_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='calendar_event_anglers_prefguides_rel',
        column1='event_id',
        column2='guides_id',
        copy=False,
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('sale_id', 'folio', 'stn_no_personas')
    def _compute_stn_precio_total(self):
        for rec in self:
            rec.stn_precio_total = rec.sale_id and rec.sale_id.amount_total or 0.0

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------
    def get_resource_extras_amount_total(self, extra=""):
        extras = self.sale_id.order_line.filtered(lambda x: x.product_id.product_tmpl_id.product_extra == extra)
        amount_total = extras and sum( extras.mapped("price_total") ) or 0.0
        return amount_total

    def get_resource_extras(self):
        SaleOrder = self.env["sale.order"] 
        for rec in self:
            sale_id = rec.sale_id
            if not sale_id:
                rec.sale_id = SaleOrder.search([('event_id', '=', rec.id)])
                sale_id = rec.sale_id

            if not sale_id:
                continue

            # Obtiene Guias
            guest_ids = sale_id.angler_line.mapped("guest_ids")
            resource_ids = sale_id.angler_line.mapped("resource_ids")
            guides_ids = sale_id.angler_line.mapped("guides_ids")
            pref_guides_ids = sale_id.angler_line.mapped("pref_guides_ids")

            rec.stn_no_personas = len(guest_ids.ids)
            rec.stn_angler_ids = guest_ids.ids
            rec.stn_no_habitaciones = len(resource_ids.ids)
            rec.stn_no_guias = len(guides_ids.ids)
            rec.stn_guides_ids = guides_ids.ids
            rec.stn_pref_guides_ids = pref_guides_ids.ids

            partner_ids = guides_ids.ids + sale_id.partner_id.ids
            rec.partner_ids = partner_ids
            rec.resource_ids = resource_ids

            return {}

    def get_sequence_name(self):
        for rec in self:
            if rec.folio != "/":
                continue
            rec.folio = self.env['ir.sequence'].next_by_code("calendar.event") or '/'

    def write(self, values):
        res = super().write(values)
        for rec in self:
            rec.get_sequence_name()
        return res

    def action_cancel_meeting(self, partner_ids):
        self.ensure_one()
        super().action_cancel_meeting(partner_ids)
        if self.active == False:
            self.sale_id.action_cancel()

