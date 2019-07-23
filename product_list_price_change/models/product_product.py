# -*- coding: utf-8 -*-
# Copyright 2019 Graeme Gellatly
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from datetime import datetime


class ProductTemplate(models.Model):
    _inherit = "product.template"

    price_change_line_ids = fields.One2many(
        string="Price Changes",
        comodel_name="product.price.change.line",
        readonly=True,
        inverse_name="product_tmpl_id",
    )


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    price_change_line_ids = fields.One2many(
        string="Price Changes",
        comodel_name="product.variant.price.change.line",
        readonly=True,
        inverse_name="product_tmpl_attribute_value_id",
    )


class ProductProduct(models.Model):

    _inherit = "product.product"

    @api.depends("product_template_attribute_value_ids.price_extra")
    def _compute_product_price_extra(self):
        to_uom = None
        if "uom" in self._context:
            to_uom = self.env["uom.uom"].browse([self._context["uom"]])
        effective_date = self._context.get(
            "date", fields.Date.context_today(self)
        )
        if isinstance(effective_date, datetime):
            effective_date = fields.Date.context_today(self, effective_date)
        fld = (
            "partner_effective_date"
            if self._context.get("partner_id")
            else "effective_date"
        )
        for product in self:
            price_extra = 0.0
            for value in product.product_template_attribute_value_ids:
                found = False
                for change in value.price_change_line_ids:
                    if change.price_change_id[fld] <= effective_date:
                        price_extra += change.price_extra
                        found = True
                        break
                if not found:
                    price_extra += value.price_extra
            if to_uom:
                price_extra = product.uom_id._compute_price(price_extra, to_uom)
            product.price_extra = price_extra

    @api.depends("list_price", "price_extra")
    def _compute_product_lst_price(self):
        to_uom = None
        if "uom" in self._context:
            to_uom = self.env["uom.uom"].browse([self._context["uom"]])
        effective_date = self._context.get(
            "date", fields.Date.context_today(self)
        )
        if isinstance(effective_date, datetime):
            effective_date = fields.Date.context_today(self, effective_date)
        fld = (
            "partner_effective_date"
            if self._context.get("partner_id")
            else "effective_date"
        )
        # only price changes before effective date, after today
        # first any customer specifc requirements
        for product in self:
            list_price = product.list_price
            for change in product.price_change_line_ids:
                if change.price_change_id[fld] <= effective_date:
                    list_price = change.list_price
                    break
            if to_uom:
                list_price = product.uom_id._compute_price(list_price, to_uom)
            product.lst_price = list_price + product.price_extra

    @api.multi
    def price_compute(self, price_type, uom=False, currency=False, company=False):
        if price_type == 'list_price':
            price_type = 'lst_price'
        return super().price_compute(price_type, uom=uom, currency=currency, company=company)