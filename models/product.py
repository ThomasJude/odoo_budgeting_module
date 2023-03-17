# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    product_fixed_budget_line = fields.One2many('product.budget.fixed', 'prod_id', 'product Fixed Budget')
    product_allocate_budget_line = fields.One2many('product.budget.allocate', 'prod_allocate_id', 'Product Allocate Budget')
    
    @api.constrains('product_allocate_budget_line')
    def total_percentage(self):
        total = 0
        for lines in self.product_allocate_budget_line:
            if lines.allocate_percent:
                total += lines.allocate_percent
        if total!=100:
            raise UserError(_("Total Percentage should be 100"))
    
class ProductBudgetFixed(models.Model):
    _name = "product.budget.fixed"
    
    name = fields.Text(string='Description', readonly=False)
        
    
    product_id = fields.Many2one('product.template','Product', index='btree_not_null')
    prod_id = fields.Many2one('product.template','Prod')
    prod_priority = fields.Integer('Priority')
    amount = fields.Float('Amount')
    assignable_status = fields.Selection([('assigned','Assigned'),('unassigned','Unassigned'),('assignable_at_inv','Assignable At Time of Invoice')], "Assignable Status")
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)
    
    bucket_type_id = fields.Many2one('bucket.type','Bucket Type')
    bucket_user= fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    # vendor_ids= fields.Many2many('res.partner',string="Bucket Item")
    prod_fix_vendor_ids = fields.Many2many(
        'res.partner', 'prod_fix_budget_vendor', 'prod_fix_budget_id', 'vendor_id',
        string='Vendors Name', copy=False)
    prod_fix_assigned_user_ids= fields.Many2many('res.users', 'prod_fix_budget_user', 'prod_fix_budget_usr_id', 'usr_id',string="Users Name",copy=False)
    
    @api.onchange('bucket_type_id')
    def _onchange_bucket_type_id(self):
        if self.bucket_type_id:
            if self.bucket_type_id.user_type:
                self.bucket_user = self.bucket_type_id.user_type
            else:
                self.bucket_user = 'etc'
        else:
            self.bucket_user = 'etc'
            
            
    @api.onchange('prod_fix_vendor_ids')
    def _onchange_prod_fix_vendor_ids(self):
        if self.prod_fix_vendor_ids:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))
            
    @api.onchange('prod_fix_assigned_user_ids')
    def _onchange_prod_fix_assigned_user_ids(self):
        if self.prod_fix_assigned_user_ids:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))
    
    
class ProductBudgetAllocate(models.Model):
    _name = "product.budget.allocate"

    name = fields.Text(string='Description', readonly=False)
    product_id = fields.Many2one('product.template', 'Product', index='btree_not_null')
    prod_allocate_id = fields.Many2one('product.template', 'Prod Allocate')
    allocate_percent = fields.Integer("%",default=0 )
    assignable_status = fields.Selection([('assigned','Assigned'),
                                          ('unassigned','Unassigned'),
                                          ('assignable_at_inv','Assignable At Time of Invoice')
                                          ],"Assignable Status",default= "unassigned")
    
    bucket_type_id = fields.Many2one('bucket.type','Bucket Type')
    bucket_user= fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    # vendor_ids= fields.Many2many('res.partner',string="Bucket Item")
    prod_remaining_budget_vendor_ids = fields.Many2many(
        'res.partner', 'prod_remaining_budget_budget_vendor', 'prod_remaining_budget_budget_id', 'vendor_id',
        string='Vendors Name', copy=False)
    prod_remaining_budget_assigned_user_ids= fields.Many2many('res.users', 'prod_remaining_budget_budget_user', 'prod_remaining_budget_budget_usr_id', 'usr_id',string="Users Name",copy=False)



    
    @api.constrains('allocate_percent')
    def _constrains_allocate_percent(self):
        for record in self:
            if record.allocate_percent>100:
                raise UserError(_("Percentage should be smaller than 100"))
            
            
            
    @api.onchange('bucket_type_id')
    def _onchange_bucket_type_id(self):
        if self.bucket_type_id:
            if self.bucket_type_id.user_type:
                self.bucket_user = self.bucket_type_id.user_type
            else:
                self.bucket_user = 'etc'
        else:
            self.bucket_user = 'etc'
            
            
    @api.onchange('prod_remaining_budget_vendor_ids')
    def _onchange_prod_remaining_budget_vendor_ids(self):
        if self.prod_remaining_budget_vendor_ids:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))
            
    @api.onchange('prod_remaining_budget_assigned_user_ids')
    def _onchange_prod_remaining_budget_assigned_user_ids(self):
        if self.prod_remaining_budget_assigned_user_ids:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))

    
    
    
    
    