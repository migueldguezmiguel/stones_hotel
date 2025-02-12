# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import  fields, models, SUPERUSER_ID

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_transportation_charges = fields.Boolean(string="Transportation Charges")

class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    is_package = fields.Boolean(string="Is Package")

    def get_ws_product_attribute_value(self, attribute_id=False):
        AttributeValueModel = self.env["product.attribute.value"].sudo()
        values = AttributeValueModel.search([("attribute_id.is_package", "=", True), ("attribute_id.id", "=", int(attribute_id))])
        vals = [{"id": "%s"%p.id, "name": p.name} for p in values]
        return vals

    def get_ws_product_packages_and_resources_OLD(self):
        resources = self.env['appointment.type'].sudo().search([]).mapped('resource_ids')
        resources_ids = [ {"id": "%s"%p.id, "name": p.name} for p in resources ]

        packages = self.env["product.attribute"].sudo().search([("is_package", "=", True)])
        packages_ids = [{"id": "%s"%p.id, "name": p.name} for p in packages]
        return packages_ids, resources_ids

    def get_ws_product_attribute_OLD(self):
        AttributeModel = self.env["product.attribute"].sudo()
        values = AttributeModel.search([("is_package", "=", True)])
        vals = [{"id": "%s"%p.id, "name": p.name} for p in values]
        return vals

    def get_product_attribute_value_appointment_OLD(self, attribute_id=False, attribute_opt_id=False):
        if attribute_id and attribute_opt_id:
            attribute_id = int(attribute_id)
            attribute_opt_id = int(attribute_opt_id)
            AppointmentModel = self.env["appointment.type"].sudo()
            ProductTemplateModel = self.env["product.template"].sudo()
            ProductTemplateValModel = self.env["product.template.attribute.value"].sudo()
            AttributeLineModel = self.env["product.template.attribute.line"].sudo()
            att_id = AttributeLineModel.search([("attribute_id", "=", attribute_id)])
            if att_id:
                appointment_id = AppointmentModel.search([("product_tmp_id", "=", att_id.product_tmpl_id.id)])
                att_val_id = ProductTemplateValModel.search([
                    ("attribute_id", "=", attribute_id), 
                    ("attribute_line_id", "=", att_id.id),
                    ("product_attribute_value_id", "=", attribute_opt_id),
                    ("product_tmpl_id", "=", att_id.product_tmpl_id.id)
                ])
                product_id = att_id.product_tmpl_id._create_product_variant(att_val_id, True)
                resources = [ {"id": "%s"%p.id, "name": p.name} for p in appointment_id.resource_ids ]
                return {
                    "product_id": product_id.id,
                    "product_tmpl_id": att_id.product_tmpl_id.id,
                    "appointment_id": appointment_id and appointment_id.id or -1,
                    "resources": resources
                }
        return {}

