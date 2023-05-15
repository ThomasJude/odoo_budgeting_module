# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class AllocationTemplate(models.Model):
    _name = "allocation.template"
    
    name = fields.Char(string='Name')
    allocation_temp_line = fields.One2many('allocation.template.line', 'allocation_temp_id', 'Allocation Template')
    is_default_temp= fields.Boolean(string='Default Template',default=False)
    
    
    @api.constrains('is_default_temp')
    def allocation_temp_is_default_temp(self):
        total = 0
        for record in self:
            obj = self.env['allocation.template'].search([('id','!=',record.id),('is_default_temp','=',True)])
            if obj:
                if record.is_default_temp:
                    raise UserError(_('There is already a Default allocation template exist'))
    
    @api.constrains('allocation_temp_line')
    def total_percentage_val(self):
        total = 0
        if self.allocation_temp_line:
            for lines in self.allocation_temp_line:
                if lines.allocate_percent:
                    total += lines.allocate_percent
            if total!=100:
                raise UserError(_("Total Percentage should be 100"))
    
    
    
    
class AllocationTemplateLine(models.Model): 
    _name = "allocation.template.line"   

    bucket_type = fields.Many2one('bucket.type',string='Bucket TYpe')
    allocate_percent = fields.Integer("%",default=0 )
    assignable_status = fields.Selection([('assigned','Assigned'),
                                          ('unassigned','Unassigned'),
                                          ('assignable_at_inv','Assignable At Time of Invoice')
                                          ],"Assignable Status",default= "unassigned")
    allocate_user_id = fields.Many2one('res.users',string='Name')
    product_id = fields.Many2one('product.template',string='Product')
    desc = fields.Text(string='Description', readonly=False)
    allocation_temp_id= fields.Many2one('allocation.template',string='Allocation Template Id')
    is_vendor = fields.Boolean(string='Is Vendor')
    
    
    @api.onchange('bucket_type')
    def _onchange_bucket_type(self):
        if self.bucket_type:
            if self.bucket_type.is_vendor:
                self.is_vendor = True
            else:
                self.is_vendor = False

        else:
            self.is_vendor = False
            
    
    
    @api.constrains('allocate_percent')
    def _constrains_allocate_percent(self):
        print ("1111111111111111111111")
        for record in self:
            if record.allocate_percent>100:
                raise UserError(_("Percentage should be smaller than 100"))
                
                
                
    @api.onchange('allocate_user_id')
    def _onchange_allocate_user_id(self):
        if self.allocate_user_id:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))
    
    # @api.onchange('product_id')
    # def fetch_vendors_data(self):
    #     if self.product_id :
    #         fetch_product_vendor = self.env['product.supplierinfo'].sudo().search(
    #             [('product_tmpl_id', '=', self.product_id.id)], limit=1,order = "id desc",)
    #         vendor_bucket_type = self.env['bucket.type'].sudo().search([('is_vendor', '=', True)])
    #         if fetch_product_vendor:
    #             self.bucket_type_id = vendor_bucket_type.id
    #             # self.prod_remaining_budget_vendor_id = fetch_product_vendor.partner_id.id
    #             self.assignable_status = 'assigned'
    #         else:
    #             self.bucket_type_id = vendor_bucket_type.id
    #             self.assignable_status = 'assignable_at_inv'


    
