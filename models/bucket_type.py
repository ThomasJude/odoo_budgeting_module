# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class BucketType(models.Model):
    _name = "bucket.type"
    
    name = fields.Char(string='Name')
    bucket_amount = fields.Float(string='Bucket Amount')
    user_type = fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")