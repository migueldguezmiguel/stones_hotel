# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from datetime import datetime, timedelta, time
from odoo.http import request
from dateutil import rrule
from odoo import _, Command, fields, models
from odoo.exceptions import UserError

class SaleResources(models.Model):
    _name = "sale.resources"
    _description = "Sale Resource"

    name = fields.Char(string="Resource", required=True, translate=True)
    resource_ids = fields.Many2many(
        comodel_name='appointment.resource',
        string="Resources", readonly=False,
        context={'active_test': False})
    image_1920 = fields.Image("Variant Image", max_width=1920, max_height=1920)
    image_1024 = fields.Image("Variant Image 1024", related="image_1920", max_width=1024, max_height=1024, store=True)
    image_512 = fields.Image("Variant Image 512", related="image_1920", max_width=512, max_height=512, store=True)
    image_256 = fields.Image("Variant Image 256", related="image_1920", max_width=256, max_height=256, store=True)
    image_128 = fields.Image("Variant Image 128", related="image_1920", max_width=128, max_height=128, store=True)

class SaleAdditionalFees(models.Model):
    _name = "sale.additional.fees"
    _description = "Sale Additional Fees"

    sequence = fields.Integer(default=1)
    active = fields.Boolean('Active', default=True)
    name = fields.Char(string="Name", required=True, translate=True)
    description = fields.Char(
        'Description', required=False,
        help="Internal Description")
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        required=True, ondelete='cascade', index=True, copy=False) 

class LineAnglerAdditionalFees(models.Model):
    _name = "line.angler.additional.fees"
    _description = "Angler Additional Fees"

    sale_order_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Line Order')
    angler_id = fields.Many2one(
        comodel_name='sale.line.angler',
        string='Angler',
        ondelete='cascade')
    additional_fees_id = fields.Many2one(
        comodel_name='sale.additional.fees',
        string="Additional Fees",
        ondelete='cascade',
        copy=False)
    extra = fields.Integer(default=0)

class SaleLineAngler(models.Model):
    _name = "sale.line.angler"
    _description = "Sale Line Angler"

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order Reference",
        required=True, ondelete='cascade', index=True, copy=False)
    line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string="Line Reference",
        required=False, 
        ondelete='cascade', index=True, copy=False)
    fees_line_ids = fields.One2many(
        'line.angler.additional.fees', 
        'angler_id', copy=False)

    # Pricing fields
    option_id = fields.Many2one(
        comodel_name='product.attribute.value',
        string="Options")

    resource_ids = fields.Many2many(
        comodel_name='appointment.resource',
        string="Resources", readonly=False,
        context={'active_test': False})
    guides_ids = fields.Many2many(
        'res.partner', 
        'sale_line_angler_guide_rel', 
        'angler_id', 
        'guide_id',
        string="Guides",
        readonly=False, 
        copy=False, 
        context={'active_test': False})    
    total_guides = fields.Integer(string="Number of Guides")

    pref_guides_ids = fields.Many2many(
        'res.partner', 
        'sale_line_angler_prefguide_rel', 
        'angler_id', 
        'guide_id',
        string="Preferred Guides",
        readonly=False, 
        copy=False, 
        context={'active_test': False})

    guest_ids = fields.Many2many(
        'res.partner', 
        'sale_line_angler_guest_rel',
        'angler_id', 
        'guest_id',
        string="Guest",
        readonly=False, 
        copy=False, 
        context={'active_test': False})
    stn_date_start = fields.Datetime(string="Date Start", index=True, readonly=True)
    stn_date_stop = fields.Datetime(string="Date Stop", index=True, readonly=True)

    def action_edit_angler(self):
        self.ensure_one()
        sale = self.order_id
        if not sale.appointment_id:
            raise UserError("Please select an appointment")
        if not sale.recurso_id:
            raise UserError("Please select an resource")
        if not sale.stn_date_start:
            raise UserError("Please select an start date")
        if not sale.stn_date_stop:
            raise UserError("Please select an end date")

        ProductAttribute = self.env["product.attribute"]
        appointment_id = sale.appointment_id or False
        template_id = appointment_id and appointment_id.product_tmpl_id and appointment_id.product_tmpl_id.id or False
        attribute_id = False
        if template_id:
            attribute_id = ProductAttribute.search([
                ('is_package', '=', True),
                ('product_tmpl_ids', 'in', [template_id])
            ], limit=1)
        additional_fees = []
        for fees in self.fees_line_ids:
            additional_fees.append({
                'sale_order_id': fees.sale_order_id,
                'additional_id': fees.additional_fees_id and fees.additional_fees_id.id or False,
                'extra': fees.extra,
                'extra_org': fees.extra
            })
        return {
            'name': 'Anglers',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'sale.order.anglers.wizard',
            'target': 'new',
            'context': {
                'default_type_action': 'edit',
                'default_option_id': self.option_id.id,
                'default_guides': self.total_guides,
                'default_angler_line_id': self.id,
                'default_guest_ids': self.guest_ids.ids,
                'default_additional_lines': additional_fees,
                'active_ids': sale.ids,
                'default_sale_id': sale.id,
                'default_partner_id': sale.partner_id and sale.partner_id.id or False,
                'default_recurso_id': sale.recurso_id and sale.recurso_id.id or False,
                'default_event_id': sale.event_id and sale.event_id.id or False,
                'default_date_from': sale.stn_date_start or False,
                'default_date_to': sale.stn_date_stop or False,
                'default_appointment_id': appointment_id and appointment_id.id or False,
                'default_additional_fees_ids': appointment_id and appointment_id.additional_fees_ids and appointment_id.additional_fees_ids.ids or False,
                'default_template_id': template_id,
                'default_attribute_id': attribute_id and attribute_id.id or False,
            },
        }

class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Lines and line based computes
    angler_line = fields.One2many(
        comodel_name='sale.line.angler',
        inverse_name='order_id',
        string="Angler Lines",
        copy=False, auto_join=True)
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
    stn_date_start = fields.Date(string="Date Start", copy=False)
    stn_date_stop = fields.Date(string="Date Stop", copy=False)

    def action_create_event(self):
        request.session["stn_sale_id"] = self.id
        datas = {}
        result = self.action_create_website_event(datas=datas)
        request.session["stn_sale_id"] = False
        request.session["stn_indx_data"] = {}
        return result

    def action_create_anglers(self):
        for sale in self:
            if not sale.appointment_id:
                raise UserError("Please select an appointment")
            if not sale.recurso_id:
                raise UserError("Please select an resource")
            if not sale.stn_date_start:
                raise UserError("Please select an start date")
            if not sale.stn_date_stop:
                raise UserError("Please select an end date")
            
            ProductAttribute = self.env["product.attribute"]
            appointment_id = sale.appointment_id or False
            template_id = appointment_id and appointment_id.product_tmpl_id and appointment_id.product_tmpl_id.id or False

            attribute_id = False
            if template_id:
                attribute_id = ProductAttribute.search([
                    ('is_package', '=', True),
                    ('product_tmpl_ids', 'in', [template_id])
                ], limit=1)
            return {
                'name': 'Anglers',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'sale.order.anglers.wizard',
                'target': 'new',
                'context': {
                    'active_ids': sale.ids,
                    'default_type_action': 'create',
                    'default_sale_id': sale.id,
                    'default_partner_id': sale.partner_id and sale.partner_id.id or False,
                    'default_recurso_id': sale.recurso_id and sale.recurso_id.id or False,
                    'default_event_id': sale.event_id and sale.event_id.id or False,
                    'default_date_from': sale.stn_date_start or False,
                    'default_date_to': sale.stn_date_stop or False,

                    'default_appointment_id': appointment_id and appointment_id.id or False,
                    'default_additional_fees_ids': appointment_id and appointment_id.additional_fees_ids and appointment_id.additional_fees_ids.ids or False,
                    'default_template_id': template_id,
                    'default_attribute_id': attribute_id and attribute_id.id or False,
                },
            }

    def get_anglers_total_guides(self):
        for sale in self:
            total_guides = sum(sale.angler_line.mapped('total_guides'))
            return total_guides

    def action_create_website_event(self, datas={}):
        guides_ids = self.angler_line.mapped("guides_ids")
        resource_ids = self.angler_line.mapped("resource_ids")
        guest_ids = self.angler_line.mapped("guest_ids")
        date_start = self.angler_line.mapped("stn_date_start")
        date_end = self.angler_line.mapped("stn_date_stop")
        admin_id = self.env.ref("base.user_admin", raise_if_not_found=False)

        if not self.event_id:
            booking_line_values = []
            for resource in resource_ids:
                booking_line_values.append({
                    'appointment_resource_id': resource.id,
                    'capacity_reserved': 1,
                    'capacity_used': 1,
                })
            event_vals = self.appointment_id._prepare_calendar_event_values(
                1, 
                booking_line_values,
                '',
                149,
                request.env['appointment.invite'],
                guides_ids,
                "",
                request.env.user.partner_id,
                request.env.user,
                date_start and date_start[0] and date_start[0].date() or "",
                date_end and date_end[0] and date_end[0].date() or "",
            )
            self.event_id = self.env["calendar.event"].create(event_vals)
            self.event_id.get_sequence_name()
        self.event_id.user_id = admin_id
        self.event_id.get_resource_extras()
        self.event_id.appointment_booker_id = self.partner_id
        return {}

    def action_create_sale_order_from_reservations(self, datas=None):
        def get_product_id(product_tmpl_id, option_id):
            product_id = False
            for tmp in product_tmpl_id:
                for line in tmp.attribute_line_ids:
                    attribute_id=line.attribute_id
                    att_id = self.env["product.template.attribute.line"].sudo().search([("attribute_id", "=", attribute_id.id)])
                    att_val_id = self.env["product.template.attribute.value"].sudo().search([
                        ("attribute_id", "=", attribute_id.id), 
                        ("attribute_line_id", "=", att_id.id),
                        ("product_attribute_value_id", "=", option_id),
                        ("product_tmpl_id", "=", product_tmpl_id.id)
                    ])
                    product_id = product_tmpl_id._create_product_variant(att_val_id, True)
            return product_id

        def get_sale_order_id(date_start, appointment_id, recurso_id, internal_note=""):
            sale_id = self.get_saleorder_portal_reservation()
            if not request.session.stn_sale_id:
                partner_id = request.env.user.partner_id
                vals_sale = {
                    'date_order': date_start,
                    'partner_id': partner_id.id,
                    'pricelist_id': partner_id.property_product_pricelist and partner_id.property_product_pricelist.id or False,
                    'state': 'draft',
                    'require_payment': False,
                    'appointment_id': appointment_id.id,
                    'recurso_id': recurso_id.id,
                    'internal_note': internal_note,
                    'user_id': request.env.user.id
                }
                sale_id = self.create(vals_sale)
                request.session["stn_sale_id"] = sale_id.id
            if sale_id:
                sale_id.internal_note = request.session.get("stn_indx_data") and request.session["stn_indx_data"].get("internal_note") or ""
            return sale_id

        AppointmentModel = self.env["appointment.type"].sudo()
        OrderLineModel = self.env['sale.order.line'].sudo()
        ProductModel = self.env['product.product'].sudo()
        TemplateModel = self.env['product.template'].sudo()
        SaleResourceModel = self.env['sale.resources'].sudo()
        SaleAdditionalModel = self.env["sale.additional.fees"].sudo()
        AnglerLineModel = self.env['sale.line.angler'].sudo()

        partner_id = request.env.user.partner_id
        product_tmpl_id = TemplateModel.browse(int(datas.get("package_id")))
        appointment_id = AppointmentModel.search([("product_tmpl_id", "=", product_tmpl_id.id)])
        recurso_id = SaleResourceModel.browse(int(datas.get("recurso_id")))

        option_id = int(datas.get("option_id"))
        additional_fees = datas.get("additional_fees")
        internal_note = ""
        if request.session.stn_indx_data:
            internal_note = request.session.get("stn_indx_data") and request.session["stn_indx_data"].get("internal_note") or ""
        
        guest_ids =  datas.get("guest_ids", [])
        pref_guides_ids =  datas.get("guia_ids", [])
        start_dt =  datas.get("date_start", "") and datas["date_start"].replace(" 00:00:00", "") or ""
        end_dt =  datas.get("date_stop", "") and datas["date_stop"].replace(" 00:00:00", "") or ""
        if isinstance(start_dt, str):
            start_dt = datetime.strptime(start_dt, '%Y-%m-%d')
        if isinstance(end_dt, str):
            end_dt = datetime.strptime(end_dt, '%Y-%m-%d')

        product_id = get_product_id(product_tmpl_id, option_id)

        # Busca RECURSOS
        habitaciones = appointment_id.get_recursos_disponibles(recurso_id, start_dt, end_dt)
        resource_ids = habitaciones.ids
        if len(resource_ids) == 0:
            return {"error": "No hay habitaciones disponibles"}
        random.shuffle( resource_ids )
        if len(resource_ids) >= 1:
            resource_ids = resource_ids[:1]                

        # Busca GUIAS
        int_guides = int(datas.get("int_guides") or "0")
        guides_ids = []
        if int_guides > 0.0:
            guias_ids = appointment_id.get_guias_disponibles(start_dt, end_dt)
            guides_ids = guias_ids.ids
            if len(guides_ids) == 0:
                return {"error": "No hay guias disponibles"}
            if len(guides_ids) < int_guides:
                return {"error": "No hay guias disponibles"}
            random.shuffle( guides_ids )
            if len(guides_ids) >= int_guides:
                guides_ids = guides_ids[:int_guides]

        sale_id = get_sale_order_id(start_dt, appointment_id, recurso_id, internal_note)
        if not sale_id.stn_date_start:
            sale_id.stn_date_start = start_dt
        if not sale_id.stn_date_stop:
            sale_id.stn_date_stop = end_dt

        if not sale_id:
            return []

        line_seq = request.session.stn_line_seq_id or 101
        if not line_seq:
            ll = OrderLineModel.search([('order_id', '=', sale_id.id), ('product_id.product_tmpl_id', '=', product_tmpl_id.id)])
            for line_seq_id in ll:
                line_seq = line_seq_id.sequence
            line_seq += 1

        sale_line_title = OrderLineModel.search([
            ('order_id', '=', sale_id.id), 
            ('sequence', '=', 100),
            ('display_type', '=', 'line_section'),
            ('name', '=', 'Package Description (Commissionable)')
        ])
        if not sale_line_title:
            request.session["stn_line_seq_id"] = 101
            sale_line_title = OrderLineModel.create({
                'order_id': sale_id.id,
                'sequence': 100,
                'display_type': 'line_section',
                'name': 'Package Description (Commissionable)',
            })
        sale_line_id = OrderLineModel.create({
            'sequence': line_seq + 1,
            'order_id': sale_id.id,
            'product_id': product_id.id,
            'product_uom_qty': len(guest_ids),
        })
        line_seq += 1
        request.session["stn_line_seq_id"] = (request.session.stn_line_seq_id or line_seq) + 1

        product_charge_id = ProductModel.search([('product_tmpl_id.is_transportation_charges', '=', True)], limit=1)
        line_charges_title = OrderLineModel.search([
            ('order_id', '=', sale_id.id), 
            ('sequence', '=', 300),
            ('display_type', '=', 'line_section'),
            ('name', '=', 'Transportation Charges (Non-Commissionable)')
        ])
        if not line_charges_title:
            line_charges_title = OrderLineModel.create({
                'order_id': sale_id.id,
                'sequence': 300,
                'display_type': 'line_section',
                'name': 'Transportation Charges (Non-Commissionable)',
            })
        # busca / crea linea de venta con producto no comisionable
        line_charges_id = OrderLineModel.search([
            ('order_id', '=', sale_id.id), 
            ('product_id', '=', product_charge_id.id)
        ], limit=1)
        if not line_charges_id:
            line_charges_id = OrderLineModel.create({
                'sequence': 301,
                'order_id': sale_id.id,
                'product_id': product_charge_id.id,
                'product_uom_qty': len(guest_ids),
            })
        else:
            line_charges_id.product_uom_qty = line_charges_id.product_uom_qty + len(guest_ids)

        angler_id = AnglerLineModel.create({
            'option_id': option_id,
            'order_id': sale_id.id,
            'line_id': sale_line_id.id,
            'guest_ids': guest_ids,
            'pref_guides_ids': pref_guides_ids,
            'total_guides': len(guides_ids),
            "guides_ids": guides_ids,
            "resource_ids": resource_ids,
            "stn_date_start": start_dt,
            "stn_date_stop": end_dt,
        })
        if additional_fees:
            line_extra_title = OrderLineModel.search([
                ('order_id', '=', sale_id.id), 
                ('sequence', '=', 200),
                ('display_type', '=', 'line_section'),
                ('name', '=', 'Other Charges/Surcharges (Non-Commissionable)')
            ], limit=1)
            if not line_extra_title:
                line_extra_title = OrderLineModel.create({
                    'order_id': sale_id.id,
                    'sequence': 200,
                    'display_type': 'line_section',
                    'name': 'Other Charges/Surcharges (Non-Commissionable)'
                })
        for additional in additional_fees:
            additional_id = SaleAdditionalModel.browse( additional["additional_fees_id"] )
            line_extra_id = OrderLineModel.search([
                ('order_id', '=', sale_id.id), 
                ('product_id', '=', additional_id.product_id.id)
            ], limit=1)
            if line_extra_id:
                line_extra_id.write({
                    'product_uom_qty': line_extra_id.product_uom_qty + additional["extra"]
                })
            elif not line_extra_id:
                line_extra_id = OrderLineModel.create({
                    'sequence': additional_id.sequence + 200,
                    'order_id': sale_id.id,
                    'product_id': additional_id.product_id.id,
                    'product_uom_qty': additional["extra"],
                })
            additional["sale_order_id"] = line_extra_id and line_extra_id.id or False

        if additional_fees:
            angler_id.write({
                "fees_line_ids": [Command.create(vals) for vals in additional_fees]
            })
        return {}

    def action_create_event_rrule(self):
        if self.event_id:
            for day_dt in rrule.rrule(freq=rrule.DAILY,
                dtstart=self.event_id.start.date(),
                until=self.event_id.stop.date(),
                interval=1):
                print("------- day_dt", day_dt)
        return []

    # PORTAL
    def get_saleorder_portal_reservation(self):
        order_id = request.session.stn_sale_id
        sale_id = self.search([("id", "=", order_id), ("state", "!=", "cancel")])
        if not sale_id.exists():
            sale_id = False
            request.session["stn_sale_id"] = False
            # request.session["stn_indx_data"] = {}
        return sale_id

    def action_cancel_prepare_anglers(self):
        EventModel = self.env['calendar.event'].sudo()
        for sale in self:
            guest_ids = sale.angler_line.mapped("guest_ids")
            resource_ids = sale.angler_line.mapped("resource_ids")
            guides_ids = sale.angler_line.mapped("guides_ids")
            event = sale.event_id
            if sale.event_id:
                event.with_context(mail_notify_author=True).action_cancel_meeting(guides_ids.ids)
                event.with_context(mail_notify_author=True).action_cancel_meeting(guest_ids.ids)
                event.show_as = 'free'
                event.action_mass_archive('all_events')

    def action_cancel(self):
        res = super().action_cancel()
        for sale in self:
            sale.with_context(cancel_internal=True).action_cancel_prepare_anglers()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def get_anglers(self):
        angler_id = self.env["sale.line.angler"].sudo().search([("line_id", "=", self.id)], limit=1)
        return angler_id

    def get_anglers_guides(self):
        angler_id = self.get_anglers()
        return angler_id and angler_id.total_guides or 0

