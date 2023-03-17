# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class BucketType(models.Model):
    _name = "bucket.type"
    
    name = fields.Char(string='Name')
    bucket_amount = fields.Float(string='Bucket Amount')
    user_type = fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    bucket_status = fields.Selection([('invoiced','Invoiced'),('released','Released')], "Bucket Status")
    
    @api.constrains('user_type','bucket_status')
    def bucket_user_type_status(self):
        total = 0
        for record in self:
            obj = self.env['bucket.type'].search([('bucket_status','=',record.bucket_status),('id','!=',record.id),('user_type','=',record.user_type)])
            if obj:
                raise UserError(_('There is already a bucket type exist with same user type and bucket status'))