# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class BucketType(models.Model):
    _name = "bucket.type"
    
    name = fields.Char(string='Name')
    # bucket_amount = fields.Float(string='Bucket Amount')
    is_vendor = fields.Boolean(string='Is Vendor')
    # user_type = fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    # bucket_status = fields.Selection([('invoiced','Invoiced'),('released','Released')], "Bucket Status")
    
    @api.constrains('is_vendor')
    def bucket_is_vendor_status(self):
        total = 0
        for record in self:
            obj = self.env['bucket.type'].search([('id','!=',record.id),('is_vendor','=',True)])
            if obj:
                if record.is_vendor:
                    raise UserError(_('There is already a bucket type exist with Vendor'))