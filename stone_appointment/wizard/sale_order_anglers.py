# -*- coding: utf-8 -*-

from odoo.http import request
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
import logging

_logger = logging.getLogger(__name__)

class SaleOrderAnglersLine(models.TransientModel):
    _name = 'sale.order.anglers.line'
    _description = "Sale Order Anglers Line"

    extra_org = fields.Integer("Extra Org")
    extra = fields.Integer("Extra")
    sale_order_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Line Order')    
    additional_id = fields.Many2one(
        comodel_name='sale.additional.fees',
        string="Additional")    
    wizard_id = fields.Many2one(
        comodel_name='sale.order.anglers.wizard',
        string="Anglers",
        required=False, 
        ondelete='cascade',
        index=True, 
        copy=False)

class SaleOrderAnglers(models.TransientModel):
    _name = 'sale.order.anglers.wizard'
    _description = 'Sale Order Anglers'

    type_action = fields.Selection([
        ('create', 'Create'),
        ('edit', 'Edita'),
    ], string="Estado")
    date_from = fields.Date(
        string="Start Date", index=True)
    date_to = fields.Date(
        string="Stop Date", index=True)
    appointment_id = fields.Many2one(
        comodel_name='appointment.type',
        string="Package Reference",
        required=False, ondelete='cascade', index=True, copy=False)
    recurso_id = fields.Many2one(
        comodel_name='sale.resources',
        string="Resource Reference",
        required=False, ondelete='cascade', index=True, copy=False)
    event_id = fields.Many2one(
        comodel_name='calendar.event',
        string="Event Reference",
        required=False, ondelete='cascade', index=True, copy=False)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Partner",
        required=False, ondelete='cascade', index=True, copy=False)
    attribute_id = fields.Many2one(
        comodel_name='product.attribute',
        string="Options")
    template_id = fields.Many2one(
        comodel_name='product.template',
        string="Template")
    sale_id = fields.Many2one(
        comodel_name='sale.order',
        string="Sale")
    additional_fees_ids = fields.Many2many(
        comodel_name='sale.additional.fees',
        string="Additional Fees", readonly=False)
    company_id = fields.Many2one(
        'res.company', string='Company', 
        required=True, 
        readonly=True, 
        index=True, 
        default=lambda self: self.env.company,
        help="Company related to this journal")
    angler_line_id = fields.Many2one(
        comodel_name='sale.line.angler',
        string="Angler Line")    

    option_id = fields.Many2one(
        comodel_name='product.attribute.value',
        string="Options")
    guides = fields.Integer("Number of guides")
    guest_ids = fields.Many2many(
        'res.partner', 
        'res_partner_order_anglers', 
        'partner_id', 
        'angler_id')
    pref_guides_ids = fields.Many2many(
        'res.partner', 
        string="Preferred Guides")
    pref_guides_tmp_ids = fields.Many2many('res.partner', compute='_compute_pref_guides_tmp_ids')

    additional_lines = fields.One2many(
        'sale.order.anglers.line', 
        'wizard_id', copy=False)


    @api.depends('sale_id')
    def _compute_pref_guides_tmp_ids(self):
        for record in self:
            sale_id = record.sale_id
            record.pref_guides_tmp_ids = sale_id.appointment_id.get_guias_disponibles(sale_id.stn_date_start, sale_id.stn_date_stop)

    #=== BASE METHODS ===#
    @api.model
    def default_get(self, fields):
        ctx = dict(self.env.context)
        res = super(SaleOrderAnglers, self).default_get(fields)
        return res

    def action_edit_anglers(self):
        OrderLineModel = self.env['sale.order.line'].sudo()
        ProductModel = self.env['product.product'].sudo()

        product_uom_qty = self.angler_line_id.line_id.product_uom_qty
        product_charge_id = ProductModel.search([
                ('product_tmpl_id.is_transportation_charges', '=', True)
            ], limit=1)
        line_charges_id = OrderLineModel.search([
            ('order_id', '=', self.sale_id.id), 
            ('product_id', '=', product_charge_id.id)
        ], limit=1)
        line_charges_id.product_uom_qty = line_charges_id.product_uom_qty - product_uom_qty
        for line in self.angler_line_id.fees_line_ids:
            sol_id = line.sale_order_id
            extra = sol_id.product_uom_qty - line.extra
            sol_id.product_uom_qty = extra
        result = self.action_create_anglers()
        self.angler_line_id.line_id.unlink()
        if self.sale_id.event_id:
            self.sale_id.action_create_website_event()
        return result

    def action_create_anglers(self):
        AppointmentModel = self.env['appointment.type'].sudo()
        CalendarModel = self.env['calendar.event'].sudo()
        PartnerModel = self.env['res.partner'].sudo()
        SaleModel = self.env['sale.order'].sudo()
        SaleResourceModel = self.env['sale.resources'].sudo()
        TemplateModel = self.env['product.template'].sudo()
        AttributeModel = self.env['product.attribute'].sudo()

        if not self.option_id:
            raise UserError("Please select an option")
        # if not self.guides:
        #     raise UserError("Please select an number of guides")
        if not self.guest_ids:
            raise UserError("Please select an guest")

        request.session["stn_sale_id"] = self.sale_id.id

        additional_fees = []
        for line in self.additional_lines:
            additional_fees.append({
                "additional_fees_id": line.additional_id and line.additional_id.id or False,
                "extra": line.extra or 0
            })
        kwargs = {
            'package_id': self.template_id and self.template_id.id or False,
            'recurso_id': self.recurso_id and self.recurso_id.id or False,
            'date_start': '%s'%self.date_from or False,
            'date_stop': '%s'%self.date_to or False,
            'option_id': self.option_id and self.option_id.id or False,
            'guest_ids': self.guest_ids and self.guest_ids.ids or False,
            'guia_ids': self.pref_guides_ids and self.pref_guides_ids.ids or False,
            'int_guides': self.guides,
            'additional_fees': additional_fees,
        }
        _logger.info('------ stn so DATAS %s '%(kwargs) )
        result = self.sale_id.action_create_sale_order_from_reservations(datas=kwargs)
        if result.get("error"):
            raise UserError( result["error"] )

        if self.sale_id.event_id:
            self.sale_id.action_create_website_event()

        request.session["stn_sale_id"] = False
        return result


