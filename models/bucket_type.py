# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class BucketType(models.Model):
    _name = "bucket.type"
    
    name = fields.Char(string='Name')
    is_vendor = fields.Boolean(string='Is Vendor')

    def unlink(self):
        if not self.env.user.has_group('odoo_budgeting_module.bucket_delete_group'):
            raise UserError("You don't have permission to delete this record.")
        return super(BucketType,self).unlink()

    @api.constrains('is_vendor')
    def bucket_is_vendor_status(self):
        total = 0
        for record in self:
            obj = self.env['bucket.type'].search([('id','!=',record.id),('is_vendor','=',True)])
            if obj:
                if record.is_vendor:
                    raise UserError(_('There is already a bucket type exist with Vendor'))