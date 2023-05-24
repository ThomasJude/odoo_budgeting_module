# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class ShowVendors(models.Model):
    _name = "show.vendors"

    name = fields.Many2one("res.partner",string='Vendor Name')
    vendor_amount = fields.Float(string='Vendor Amount',)
    bucket_id = fields.Many2one('bucket', 'Bucket')