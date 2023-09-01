# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class BucketType(models.Model):
    _name = "bucket.type"
    
    name = fields.Char(string='Name')
    # is_vendor = fields.Boolean(string='Is Vendor')

    def unlink(self):
        if not self.env.user.has_group('odoo_budgeting_module.bucket_delete_group'):
            raise UserError("You don't have permission to delete this record.")
        bucket = self.env['bucket'].search([('bucket_type_id','=',self.id)])
        product_fixed = self.env['product.budget.fixed'].search([('bucket_type_id','=',self.id)])
        product_allocate = self.env['product.budget.allocate'].search([('bucket_type_id','=',self.id)])
        allocation_template = self.env['allocation.template.line'].search([('bucket_type','=',self.id)])
        for rec in bucket:
            if rec.bucket_amount > 0.0 or len(product_fixed) > 0 or \
                    len(product_allocate) > 0 or len(allocation_template) > 0:
                raise UserError("Bucket Type has been used in Invoices/Products/Budget Allocation Templates.")
        return super(BucketType,self).unlink()

    @api.constrains('name')
    def _check_name_duplicacy(self):
        buckettype = self.env['bucket.type'].search([('name', '=', self.name), ('id', '!=', self.id)])
        if buckettype:
            raise UserError(_('Already a Bucket Type Exists ! '))

    # @api.constrains('is_vendor')
    # def bucket_is_vendor_status(self):
    #     total = 0
    #     for record in self:
    #         obj = self.env['bucket.type'].search([('id','!=',record.id),('is_vendor','=',True)])
    #         if obj:
    #             if record.is_vendor:
    #                 raise UserError(_('There is already a bucket type exist with Vendor'))

    @api.model_create_multi
    def create(self, vals_list):

        res = super(BucketType,self).create(vals_list)
        for rec in res:
            inv_bucket_id= self.env['bucket'].sudo().create({"name": rec.name, 'bucket_status': 'invoiced','bucket_type_id':rec.id})
            rel_bucket_id= self.env['bucket'].sudo().create({"name": rec.name, 'bucket_status': 'released','bucket_type_id':rec.id})
            bil_bucket_id= self.env['bucket'].sudo().create({"name": rec.name, 'bucket_status': 'billed','bucket_type_id':rec.id})
        return res