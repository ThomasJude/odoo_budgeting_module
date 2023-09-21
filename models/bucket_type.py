# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class BucketType(models.Model):
    _name = "bucket.type"
    _parent_name = "sub_buckettype"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'
    
    name = fields.Char(string='Name')
    sub_buckettype = fields.Many2one('bucket.type','Parent Bucket',index=True, ondelete='cascade')
    complete_name = fields.Char(
        'Name', compute='_compute_complete_name', recursive=True,
        store=True)
    parent_path = fields.Char(index=True, unaccent=False)
    # is_parent = fields.Boolean(string='Is Sales Person')
    # is_vendor = fields.Boolean(string='Is Vendor')

    @api.depends('name', 'sub_buckettype.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.sub_buckettype:
                category.complete_name = '%s / %s' % (category.sub_buckettype.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    def name_get(self):
        if not self.env.context.get('hierarchical_naming', True):
            return [(record.id, record.name) for record in self]
        return super().name_get()

    def unlink(self):
        if not self.env.user.has_group('odoo_budgeting_module.bucket_delete_group'):
            raise UserError("You don't have permission to delete this record.")
        for res in self:
            bucket = self.env['bucket'].search([('bucket_type_id','=',res.id)])
            product_fixed = self.env['product.budget.fixed'].search([('bucket_type_id','=',res.id)])
            product_allocate = self.env['product.budget.allocate'].search([('bucket_type_id','=',res.id)])
            allocation_template = self.env['allocation.template.line'].search([('bucket_type','=',res.id)])
            for rec in bucket:
                if rec.bucket_amount > 0.0 or len(product_fixed) > 0 or \
                        len(product_allocate) > 0 or len(allocation_template) > 0:
                    raise UserError("Bucket Type has been used in Invoices/Products/Budget Allocation Templates.")
        return super(BucketType,self).unlink()

    @api.constrains('name')
    def _check_name_duplicacy(self):
        buckettype = self.env['bucket.type'].search([('name', '=', self.name),('id', '!=', self.id)])
        if buckettype:
            raise UserError(_('Already a Bucket Type Exists ! '))

    # @api.constrains('is_salesperson')
    # def bucket_is_vendor_status(self):
    #     total = 0
    #     for record in self:
    #         obj = self.env['bucket.type'].search([('id','!=',record.id),('is_salesperson','=',True)])
    #         if obj:
    #             if record.is_salesperson:
    #                 raise UserError(_('There is already a bucket type exist with Sales Person'))

    @api.model_create_multi
    def create(self, vals_list):

        res = super(BucketType,self).create(vals_list)
        if not res.sub_buckettype:
            for rec in res:
                inv_bucket_id= self.env['bucket'].sudo().create({"name": rec.name, 'bucket_status': 'invoiced','bucket_type_id':rec.id})
                rel_bucket_id= self.env['bucket'].sudo().create({"name": rec.name, 'bucket_status': 'released','bucket_type_id':rec.id})
                bil_bucket_id= self.env['bucket'].sudo().create({"name": rec.name, 'bucket_status': 'billed','bucket_type_id':rec.id})
        return res
