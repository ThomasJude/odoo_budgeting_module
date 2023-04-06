# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    product_fixed_budget_line = fields.One2many('product.budget.fixed', 'prod_id', 'product Fixed Budget')
    product_allocate_budget_line = fields.One2many('product.budget.allocate', 'prod_allocate_id', 'Product Allocate Budget')
    
    
    
    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        print(vals)
        # for product_fixed_budget_line,val in zip(self.product_fixed_budget_line,vals.get('product_fixed_budget_line')):
        #     if val[1] != product_fixed_budget_line.id:
        #         print(val[1], product_fixed_budget_line.id)
        #         existing_prod_priority = self.env['product.budget.fixed'].sudo().search(
        #             [('prod_priority', '=', product_fixed_budget_line.prod_priority),('prod_id','=',self.id)])
        #         print("DDDDVVVVVVVVV",existing_prod_priority,self.id,product_fixed_budget_line.prod_priority)
        #         if existing_prod_priority:
        #             raise UserError(_('Product priority should be unique in Fixed Reduction budgeting tab'))

        product_product_id = self.env['product.product'].sudo().search([('product_tmpl_id','=',self.id)])
        invoices_lines = self.env['account.move.line'].sudo().search([('product_id','=',product_product_id.id)])
        # print("NNNNNNNNNNNNNNNNNNN",invoices_lines.move_id.state)
        for invoice in invoices_lines:
            if invoice.move_id.state == 'draft':
                for inv_budget_line in invoice.move_id.inv_budget_line:
                    print('SAADDDDD',inv_budget_line.account_move_line_id,invoice.id)
                    if inv_budget_line.account_move_line_id.id == invoice.id:
                        inv_budget_line.unlink()
                for remain_budget_line in invoice.move_id.product_remaining_budget_line:
                    print('SAADDDDD',remain_budget_line.account_move_line_id,invoice.id)
                    if remain_budget_line.account_move_line_id.id == invoice.id:
                        remain_budget_line.unlink()
                if invoice.product_id and invoice.product_id.product_tmpl_id and invoice.product_id.product_fixed_budget_line:
                    for fix_budget_line in self.product_fixed_budget_line:
                        budget_data = self.env['invoice.budget.line'].sudo().create({
                            'product_id_budget': fix_budget_line.product_id.id,
                            'name': fix_budget_line.name,
                            'prod_inv_id': invoice.move_id.id,
                            'account_move_line_id': invoice.id,
                            'bucket_type_id': fix_budget_line.bucket_type_id.id,
                            'assignable_status': fix_budget_line.assignable_status,
                            'amount': fix_budget_line.amount * invoice.quantity,
                            'is_vendor':fix_budget_line.is_vendor,
                            # 'bucket_user': fix_budget_line.bucket_user,
                            # 'budget_inv_vendor_ids': [(6,0, fix_budget_line.prod_fix_vendor_ids.ids)] or [],
                            'budget_inv_vendor_id': fix_budget_line.prod_fix_vendor_id.id,
                            # 'budget_user_ids':[(6,0, fix_budget_line.prod_fix_assigned_user_ids.ids)] or [],
                            'budget_user_id': fix_budget_line.prod_fix_assigned_user_id.id,
                            'prod_priority': fix_budget_line.prod_priority,
                            # 'fixed_budget_line_id': fix_budget_line.id
                        })
                if invoice.product_id and invoice.product_id.product_tmpl_id and invoice.product_id.product_allocate_budget_line:
                    for allocate_budget_line in self.product_allocate_budget_line:
                        remaining_budget_data = self.env['product.budget.remaining'].sudo().create({
                            'product_id_budget': allocate_budget_line.product_id.id,
                            'name': allocate_budget_line.name,
                            'prod_remaining_id': invoice.move_id.id,
                            'account_move_line_id': invoice.id,
                            
                            'bucket_type_id': allocate_budget_line.bucket_type_id.id,
                            'assignable_status': allocate_budget_line.assignable_status,
                            # 'bucket_user': allocate_budget_line.bucket_user,
                            'is_vendor':allocate_budget_line.is_vendor,
                            # 'budget_inv_remaining_vendor_ids': [(6,0, allocate_budget_line.prod_remaining_budget_vendor_ids.ids)] or [],
                            'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
                            # 'budget_remaining_user_ids':[(6,0, allocate_budget_line.prod_remaining_budget_assigned_user_ids.ids)] or [],
                            'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
                            'allocate_percent': allocate_budget_line.allocate_percent,
                            'amount': allocate_budget_line.amount * invoice.quantity
                        })

        return res
    
    
    # @api.constrains('product_fixed_budget_line,product_fixed_budget_line.prod_priority')
    # def prod_priority_val(self):
    #     print ("2222222222222222")
    #     lst = []
    #     for rec in self:
    #         if self.product_fixed_budget_line:
    #             for fixed_item in self.product_fixed_budget_line:
    #                 if fixed_item.prod_priority not in lst:
    #                     lst.append(fixed_item.prod_priority)
    #                 else:
    #                     raise UserError(_('Product priority should be unique in Fixed Reduction budgeting tab'))
    
    
    # @api.constrains('product_fixed_budget_line,product_fixed_budget_line.prod_priority')
    # def prod_priority_val(self):
    #     total = 0
    #     for rec in self:
    #         obj = self.env['product.budget.fixed'].search([('id','!=',rec.id),('prod_priority','=',rec.prod_priority)])
    #         if obj:
    #             raise UserError(_('Product priority should be unique in Fixed Reduction budgeting tab'))
    
    @api.constrains('product_fixed_budget_line',"list_price")
    def selling_amount_check(self):
        total = 0
        if self.product_fixed_budget_line:
            for lines in self.product_fixed_budget_line:
                if lines.amount:
                    total += lines.amount
            self.product_allocate_budget_line._constrains_allocate_percent()
        if total > self.list_price:
            raise UserError(_("Total of Fixed Reductions should not be Greater than Selling Price"))

    @api.constrains('list_price')
    def calculate_percentage_allocation(self):
        self.product_allocate_budget_line._constrains_allocate_percent()
    
    
    
    @api.constrains('product_allocate_budget_line')
    def total_percentage(self):
        total = 0
        if self.product_allocate_budget_line:
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
    is_vendor = fields.Boolean(string='Is Vendor')
    # bucket_user= fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    prod_fix_vendor_id = fields.Many2one('res.partner', string='Vendor Name', copy=False)
    # prod_fix_assigned_user_ids = fields.Many2many('res.users', 'prod_fix_budget_user', 'prod_fix_budget_usr_id', 'usr_id',string="Users Name",copy=False)
    prod_fix_assigned_user_id = fields.Many2one('res.users', string="User Name", copy=False)
    
    
    
    @api.onchange('bucket_type_id')
    def _onchange_bucket_type_id(self):
        if self.bucket_type_id:
            if self.bucket_type_id.is_vendor:
                self.is_vendor = True
            else:
                self.is_vendor=False
        else:
            self.is_vendor=False
    
    
    # @api.onchange('bucket_type_id')
    # def _onchange_bucket_type_id(self):
    #     if self.bucket_type_id:
    #         if self.bucket_type_id.user_type:
    #             self.bucket_user = self.bucket_type_id.user_type
    #         else:
    #             self.bucket_user = 'etc'
    #     else:
    #         self.bucket_user = 'etc'

    @api.onchange('product_id')
    def _onchange_product_amount(self):
        if self.product_id.standard_price:
            self.amount = self.product_id.standard_price

    @api.onchange('assignable_status')
    def _onchange_vendor_name(self):
        if self.assignable_status or self.assignable_status == False:
            self.prod_fix_vendor_id = False or None
            self.prod_fix_assigned_user_id = False or None

    @api.onchange('bucket_type_id')
    def _onchange_bucket_type(self):
        if self.bucket_type_id:
            self.prod_fix_vendor_id = False or None
            self.prod_fix_assigned_user_id = False or None
            self.assignable_status = False
            
    # @api.onchange('prod_fix_vendor_ids')
    # def _onchange_prod_fix_vendor_ids(self):
    #     if self.prod_fix_vendor_ids:
    #         if not self.assignable_status:
    #             raise UserError(_('1st select the Assignable status'))

    @api.onchange('prod_fix_vendor_id')
    def _onchange_prod_fix_vendor_id(self):
        if self.prod_fix_vendor_id:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))
            
    # @api.onchange('prod_fix_assigned_user_ids')
    # def _onchange_prod_fix_assigned_user_ids(self):
    #     if self.prod_fix_assigned_user_ids:
    #         if not self.assignable_status:
    #             raise UserError(_('1st select the Assignable status'))

    @api.onchange('prod_fix_assigned_user_id')
    def _onchange_prod_fix_assigned_user_id(self):
        if self.prod_fix_assigned_user_id:
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
    is_vendor = fields.Boolean(string='Is Vendor')
    # bucket_user= fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    # vendor_ids= fields.Many2many('res.partner',string="Bucket Item")
    # prod_remaining_budget_vendor_ids = fields.Many2many(
    #     'res.partner', 'prod_remaining_budget_budget_vendor', 'prod_remaining_budget_budget_id', 'vendor_id',
    #     string='Vendors Name', copy=False)
    prod_remaining_budget_vendor_id = fields.Many2one('res.partner', string="Vendors Name", copy=False)
    # prod_remaining_budget_assigned_user_ids= fields.Many2many('res.users', 'prod_remaining_budget_budget_user', 'prod_remaining_budget_budget_usr_id', 'usr_id',string="Users Name",copy=False)
    prod_remaining_budget_assigned_user_id = fields.Many2one('res.users', string="Users Name", copy=False)
    amount = fields.Float("amount")


    
    @api.constrains('allocate_percent')
    def _constrains_allocate_percent(self):
        for record in self:
            if record.allocate_percent>100:
                raise UserError(_("Percentage should be smaller than 100"))
            elif record.allocate_percent:
                total_fixed_reduction=0
                for fixed_reduction_line in record.prod_allocate_id.product_fixed_budget_line:
                    if fixed_reduction_line.amount:
                        total_fixed_reduction += fixed_reduction_line.amount
                remaining_percent_allocation_amount = record.prod_allocate_id.list_price - total_fixed_reduction
                record.amount = remaining_percent_allocation_amount*record.allocate_percent/100
                
                
                
    @api.onchange('bucket_type_id')
    def _onchange_bucket_type_id(self):
        if self.bucket_type_id:
            if self.bucket_type_id.is_vendor:
                self.is_vendor = True
            else:
                self.is_vendor = False
        else:
            self.is_vendor = False
            
            
            
    # @api.onchange('bucket_type_id')
    # def _onchange_bucket_type_id(self):
    #     if self.bucket_type_id:
    #         if self.bucket_type_id.user_type:
    #             self.bucket_user = self.bucket_type_id.user_type
    #         else:
    #             self.bucket_user = 'etc'
    #     else:
    #         self.bucket_user = 'etc'
            
            
    # @api.onchange('prod_remaining_budget_vendor_ids')
    # def _onchange_prod_remaining_budget_vendor_ids(self):
    #     if self.prod_remaining_budget_vendor_ids:
    #         if not self.assignable_status:
    #             raise UserError(_('1st select the Assignable status'))
            
    @api.onchange('prod_remaining_budget_vendor_id')
    def _onchange_prod_remaining_budget_vendor_id(self):
        if self.prod_remaining_budget_vendor_id:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))
            
    # @api.onchange('prod_remaining_budget_assigned_user_ids')
    # def _onchange_prod_remaining_budget_assigned_user_ids(self):
    #     if self.prod_remaining_budget_assigned_user_ids:
    #         if not self.assignable_status:
    #             raise UserError(_('1st select the Assignable status'))
            
    @api.onchange('prod_remaining_budget_assigned_user_id')
    def _onchange_prod_remaining_budget_assigned_user_id(self):
        if self.prod_remaining_budget_assigned_user_id:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))

    
    
    
    
    