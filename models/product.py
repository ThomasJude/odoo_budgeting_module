# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    remaining_allocation_temp = fields.Many2one('allocation.template',string='Remaining Allocation Template')
    product_fixed_budget_line = fields.One2many('product.budget.fixed', 'prod_id', 'product Fixed Budget')
    product_allocate_budget_line = fields.One2many('product.budget.allocate', 'prod_allocate_id', 'Product Allocate Budget')
    
    @api.onchange('remaining_allocation_temp')
    def remaining_allocation_temp_data_val (self):

        lst = []  
        if self.remaining_allocation_temp:
            if self.remaining_allocation_temp.allocation_temp_line:
                for remaining_allocation in self.remaining_allocation_temp.allocation_temp_line:
                    lst.append([0,0,{
                                        'product_id': remaining_allocation.product_id.id,
                                        'name': remaining_allocation.desc,
                                        'bucket_type_id': remaining_allocation.bucket_type.id,
                                        'assignable_status': remaining_allocation.assignable_status,
                                        'is_vendor': remaining_allocation.is_vendor,
                                        'prod_allocate_id': self.id,
                                        'prod_remaining_budget_assigned_user_id': remaining_allocation.allocate_user_id.id,
                                        'allocate_percent': remaining_allocation.allocate_percent,
                                        'allocation_temp_id':self.remaining_allocation_temp.id
                                    }])
        print('lst',lst)
        self.product_allocate_budget_line = False
        self.write({'product_allocate_budget_line' : lst})
        return 
    
    
    # @api.onchange('remaining_allocation_temp')
    # def remaining_allocation_temp_data_val(self):
    #     print ("aaaaaaaaaaaaaaaaaaaaa",self.remaining_allocation_temp.name)
    #
    #     if self.remaining_allocation_temp:
    #         if self.remaining_allocation_temp.allocation_temp_line:
    #             for remaining_allocation in self.remaining_allocation_temp.allocation_temp_line:
    #                 remaining_budget_data = self.env['product.budget.allocate'].sudo().create({
    #                                 'product_id': remaining_allocation.product_id.id,
    #                                 'name': remaining_allocation.desc,
    #                                 'bucket_type_id': remaining_allocation.bucket_type.id,
    #                                 'assignable_status': remaining_allocation.assignable_status,
    #                                 'is_vendor': remaining_allocation.is_vendor,
    #                                 'prod_allocate_id': self.id,
    #                                 'prod_remaining_budget_assigned_user_id': remaining_allocation.allocate_user_id.id,
    #                                 'allocate_percent': remaining_allocation.allocate_percent,
    #                                 'allocation_temp_id':self.remaining_allocation_temp.id
    #                             })
    #
    #     lst=[]
    #     if self.product_allocate_budget_line:
    #         for all in self.product_allocate_budget_line:
    #             if all.allocation_temp_id.id != self.remaining_allocation_temp.id:
    #                 lst.append(all)
    #
    #
    #         self.product_allocate_budget_line.remove(lst)
            
                    
    
    @api.onchange('product_fixed_budget_line')
    def calculate_remaining_check(self):
        total_cost_val=0.0
        if self.product_fixed_budget_line:
            for fixed in self.product_fixed_budget_line:
                total_cost_val=total_cost_val+fixed.amount
        self.standard_price = total_cost_val
            
        self.product_allocate_budget_line._constrains_allocate_percent()
    
    
    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if vals.get("seller_ids"):
            fixed_budget_product = self.env['product.budget.fixed'].sudo().search([('product_id','=',self.id),('is_vendor','=',True)])

            inv_fixed_budget_liness= self.env['invoice.budget.line'].sudo().search([('product_id_budget','=',self.id)])
            for fixed_inv_budgtt in inv_fixed_budget_liness:
                if fixed_inv_budgtt.prod_inv_id.state == 'draft':
                    fixed_inv_budgtt.amount= fixed_inv_budgtt.product_id_budget.standard_price
            
            for product in fixed_budget_product:
                product_product_id = self.env['product.product'].sudo().search(
                    [('product_tmpl_id', '=', product.prod_id.id)])
                
                product.amount= self.standard_price
                invoices_lines = self.env['account.move.line'].sudo().search([('product_id', '=', product_product_id.id)])
                # print("NNNNNNNNNNNNNNNNNNN",invoices_lines.move_id.state)
                for invoice in invoices_lines:
                    if invoice.move_id.state == 'draft':
                        for inv_budget_line in invoice.move_id.inv_budget_line:
                            # print('SAADDDDD',inv_budget_line.account_move_line_id,invoice.id)
                            if inv_budget_line.account_move_line_id.id == invoice.id:
                                inv_budget_line.unlink()
                        for remain_budget_line in invoice.move_id.product_remaining_budget_line:
                            # print('SAADDDDD',remain_budget_line.account_move_line_id,invoice.id)
                            if remain_budget_line.account_move_line_id.id == invoice.id:
                                remain_budget_line.unlink()
                        if invoice.product_id and invoice.product_id.product_tmpl_id and invoice.product_id.product_fixed_budget_line:
                            for fix_budget_line in product.prod_id.product_fixed_budget_line:
                                budget_data = self.env['invoice.budget.line'].sudo().create({
                                    'product_id_budget': fix_budget_line.product_id.id,
                                    'name': fix_budget_line.name,
                                    'prod_inv_id': invoice.move_id.id,
                                    'account_move_line_id': invoice.id,
                                    'bucket_type_id': fix_budget_line.bucket_type_id.id,
                                    'assignable_status': fix_budget_line.assignable_status,
                                    'amount': fix_budget_line.amount * invoice.quantity,
                                    'is_vendor': fix_budget_line.is_vendor,
                                    # 'bucket_user': fix_budget_line.bucket_user,
                                    # 'budget_inv_vendor_ids': [(6,0, fix_budget_line.prod_fix_vendor_ids.ids)] or [],
                                    'budget_inv_vendor_id': fix_budget_line.prod_fix_vendor_id.id,
                                    # 'budget_user_ids':[(6,0, fix_budget_line.prod_fix_assigned_user_ids.ids)] or [],
                                    'budget_user_id': fix_budget_line.prod_fix_assigned_user_id.id,
                                    'prod_priority': fix_budget_line.prod_priority,
                                    # 'fixed_budget_line_id': fix_budget_line.id
                                })
                        if invoice.product_id and invoice.product_id.product_tmpl_id and invoice.product_id.product_allocate_budget_line:
                            for allocate_budget_line in product.prod_id.product_allocate_budget_line:
                                remaining_budget_data = self.env['product.budget.remaining'].sudo().create({
                                    'product_id_budget': allocate_budget_line.product_id.id,
                                    'name': allocate_budget_line.name,
                                    'prod_remaining_id': invoice.move_id.id,
                                    'account_move_line_id': invoice.id,

                                    'bucket_type_id': allocate_budget_line.bucket_type_id.id,
                                    'assignable_status': allocate_budget_line.assignable_status,
                                    # 'bucket_user': allocate_budget_line.bucket_user,
                                    'is_vendor': allocate_budget_line.is_vendor,
                                    # 'budget_inv_remaining_vendor_ids': [(6,0, allocate_budget_line.prod_remaining_budget_vendor_ids.ids)] or [],
                                    'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
                                    # 'budget_remaining_user_ids':[(6,0, allocate_budget_line.prod_remaining_budget_assigned_user_ids.ids)] or [],
                                    'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
                                    'allocate_percent': allocate_budget_line.allocate_percent,
                                    'amount': allocate_budget_line.amount * invoice.quantity
                                })
        
        elif vals.get('standard_price') and not vals.get('product_fixed_budget_line') :
            product_product_id = self.env['product.product'].sudo().search([('product_tmpl_id', '=', self.id)])

            prod_fixed_budget_lines = self.env['product.budget.fixed'].sudo().search([('product_id', '=', self.id)])
            for fixed_budgt in prod_fixed_budget_lines:
                fixed_budgt.amount= product_product_id.standard_price


            prod_inv_line = self.env['invoice.budget.line'].sudo().search([('product_id_budget','=',self.id)])
            # for all_invoices in prod_inv_line:
            # print("product in fixed inv lines",prod_inv_line)
            if prod_fixed_budget_lines:
                for inv_product in prod_fixed_budget_lines:
                    moveline_product_id = self.env['product.product'].sudo().search(
                        [('product_tmpl_id', '=', inv_product.prod_id.id)])

                    invoices_lines = self.env['account.move.line'].sudo().search([('product_id', '=', moveline_product_id.id)])
                    for invoice in invoices_lines:
                        print("jjjjjjjjjjjjj", invoice.id)
                        if invoice.move_id.state == 'draft':
                            for inv_budget_line in invoice.move_id.inv_budget_line:
                                # print('SAADDDDD',inv_budget_line.account_move_line_id,invoice.id)
                                if inv_budget_line.account_move_line_id.id == invoice.id:
                                    inv_budget_line.unlink()
                            for remain_budget_line in invoice.move_id.product_remaining_budget_line:
                                # print('SAADDDDD',remain_budget_line.account_move_line_id,invoice.id)
                                if remain_budget_line.account_move_line_id.id == invoice.id:
                                    remain_budget_line.unlink()
                            if invoice.product_id and invoice.product_id.product_tmpl_id and invoice.product_id.product_fixed_budget_line:
                                for fix_budget_line in inv_product.prod_id.product_fixed_budget_line:
                                    budget_data = self.env['invoice.budget.line'].sudo().create({
                                        'product_id_budget': fix_budget_line.product_id.id,
                                        'name': fix_budget_line.name,
                                        'prod_inv_id': invoice.move_id.id,
                                        'account_move_line_id': invoice.id,
                                        'bucket_type_id': fix_budget_line.bucket_type_id.id,
                                        'assignable_status': fix_budget_line.assignable_status,
                                        'amount': fix_budget_line.amount * invoice.quantity,
                                        'is_vendor': fix_budget_line.is_vendor,
                                        # 'bucket_user': fix_budget_line.bucket_user,
                                        # 'budget_inv_vendor_ids': [(6,0, fix_budget_line.prod_fix_vendor_ids.ids)] or [],
                                        'budget_inv_vendor_id': fix_budget_line.prod_fix_vendor_id.id,
                                        # 'budget_user_ids':[(6,0, fix_budget_line.prod_fix_assigned_user_ids.ids)] or [],
                                        'budget_user_id': fix_budget_line.prod_fix_assigned_user_id.id,
                                        'prod_priority': fix_budget_line.prod_priority,
                                        # 'fixed_budget_line_id': fix_budget_line.id
                                    })
                            if invoice.product_id and invoice.product_id.product_tmpl_id and invoice.product_id.product_allocate_budget_line:
                                for allocate_budget_line in inv_product.prod_id.product_allocate_budget_line:
                                    remaining_budget_data = self.env['product.budget.remaining'].sudo().create({
                                        'product_id_budget': allocate_budget_line.product_id.id,
                                        'name': allocate_budget_line.name,
                                        'prod_remaining_id': invoice.move_id.id,
                                        'account_move_line_id': invoice.id,

                                        'bucket_type_id': allocate_budget_line.bucket_type_id.id,
                                        'assignable_status': allocate_budget_line.assignable_status,
                                        # 'bucket_user': allocate_budget_line.bucket_user,
                                        'is_vendor': allocate_budget_line.is_vendor,
                                        # 'budget_inv_remaining_vendor_ids': [(6,0, allocate_budget_line.prod_remaining_budget_vendor_ids.ids)] or [],
                                        'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
                                        # 'budget_remaining_user_ids':[(6,0, allocate_budget_line.prod_remaining_budget_assigned_user_ids.ids)] or [],
                                        'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
                                        'allocate_percent': allocate_budget_line.allocate_percent,
                                        'amount': allocate_budget_line.amount * invoice.quantity
                                    })

        else:
            product_product_id = self.env['product.product'].sudo().search([('product_tmpl_id','=',self.id)])

            invoices_lines = self.env['account.move.line'].sudo().search([('product_id','=',product_product_id.id)])

            for invoice in invoices_lines:
                if invoice.move_id.state == 'draft':
                    for inv_budget_line in invoice.move_id.inv_budget_line:
                        if inv_budget_line.account_move_line_id.id == invoice.id:
                            inv_budget_line.unlink()
                    for remain_budget_line in invoice.move_id.product_remaining_budget_line:
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
                            print("XXXXXXCCCCCCC",allocate_budget_line.name,allocate_budget_line.amount)
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
        
        
    @api.constrains('product_fixed_budget_line','product_fixed_budget_line.bucket_type_id','product_fixed_budget_line.assignable_status')
    def vendor_user_allocation_assigned_status(self):
        total_cost_Val=0.0
        if self.product_fixed_budget_line:
            for fixed_budg in self.product_fixed_budget_line:
                total_cost_Val= total_cost_Val+ fixed_budg.amount
                if fixed_budg.bucket_type_id.is_vendor and fixed_budg.assignable_status == 'assigned':
                    if not fixed_budg.prod_fix_vendor_id:
                        raise UserError(_("Please add vendor for assigned status fixed reduction budgeting tab "))
                    
                if not fixed_budg.bucket_type_id.is_vendor and fixed_budg.assignable_status == 'assigned':
                    if not fixed_budg.prod_fix_assigned_user_id:
                        raise UserError(_("Please add User for assigned status fixed reduction budgeting tab "))
                    
            self.standard_price = total_cost_Val
                    
                    
    @api.constrains('product_allocate_budget_line','product_allocate_budget_line.bucket_type_id','product_allocate_budget_line.assignable_status')
    def remaining_vendor_user_allocation_assigned_status(self):
        if self.product_allocate_budget_line:
            for rem_budg in self.product_allocate_budget_line:
                if rem_budg.bucket_type_id.is_vendor and rem_budg.assignable_status == 'assigned':
                    if not rem_budg.prod_remaining_budget_vendor_id:
                        raise UserError(_("Please add vendor for assigned status Remaining Allocation budgeting tab "))
                    
                if not rem_budg.bucket_type_id.is_vendor and rem_budg.assignable_status == 'assigned':
                    if not rem_budg.prod_remaining_budget_assigned_user_id:
                        raise UserError(_("Please add User for assigned status Remaining Allocation budgeting tab "))
        
        
    # @api.constrains('product_fixed_budget_line','product_fixed_budget_line.bucket_type_id')
    # def bucket_type_allocation(self):
    #     if self.product_fixed_budget_line:
    #         for fixed_budg in self.product_fixed_budget_line:
    #             if not fixed_budg.bucket_type_id:
    #                 raise UserError(_("Please add bucket type in fixed reduction budgeting tab"))
                    
    
    
    
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
    
    
    @api.constrains('amount')
    def calculate_remaining_amount(self):
        self.prod_id.product_allocate_budget_line._constrains_allocate_percent()
    
    
    @api.onchange('product_id')
    def fetch_vendors(self):
        if self.product_id:
            fetch_product_vendor = self.env['product.supplierinfo'].sudo().search([('product_tmpl_id','=',self.product_id.id)],limit=1,order = "id desc",)
            vendor_bucket_type = self.env['bucket.type'].sudo().search([('is_vendor', '=', True)])
            if fetch_product_vendor:
                self.bucket_type_id = vendor_bucket_type.id
                self.prod_fix_vendor_id = fetch_product_vendor.partner_id.id
                self.assignable_status = 'assigned'
            else:
                self.bucket_type_id = vendor_bucket_type.id
                self.assignable_status = 'assignable_at_inv'
    
    
    
    @api.onchange('bucket_type_id')
    def _onchange_bucket_type(self):
        if self.bucket_type_id.is_vendor:
            self.prod_fix_vendor_id = False or None
            self.prod_fix_assigned_user_id = False or None

            fetch_product_vendor = self.env['product.supplierinfo'].sudo().search([('product_tmpl_id','=',self.product_id.id)],limit=1,order = "id desc",)

            if not fetch_product_vendor:
                self.assignable_status = 'assignable_at_inv'
            else:
                self.prod_fix_vendor_id = fetch_product_vendor.partner_id.id
                self.assignable_status = 'assigned'
        else:

            self.prod_fix_vendor_id = False or None
            self.prod_fix_assigned_user_id = False or None
            self.assignable_status = 'assignable_at_inv'

    

    @api.onchange('product_id')
    def _onchange_product_amount(self):
        if self.product_id.standard_price:
            self.amount = self.product_id.standard_price

    @api.onchange('assignable_status')
    def _onchange_vendor_name(self):
        if self.assignable_status or self.assignable_status == False:
            if self.assignable_status != 'assigned':
                self.prod_fix_vendor_id = False or None
                self.prod_fix_assigned_user_id = False or None
            else:
                fetch_product_vendor = self.env['product.supplierinfo'].sudo().search(
                    [('product_tmpl_id', '=', self.product_id.id)], limit=1, order="id desc", )

                if not fetch_product_vendor:
                    if self.bucket_type_id.is_vendor:
                        self.assignable_status = 'assignable_at_inv'
                else:
                    if self.bucket_type_id.is_vendor:
                        self.prod_fix_vendor_id = fetch_product_vendor.partner_id.id
                    self.assignable_status = 'assigned'

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
    allocation_temp_id= fields.Many2one('allocation.template', string="Template", copy=False)
    
    @api.onchange('product_id')
    def fetch_vendors(self):
        if self.product_id :
            fetch_product_vendor = self.env['product.supplierinfo'].sudo().search(
                [('product_tmpl_id', '=', self.product_id.id)], limit=1,order = "id desc",)
            vendor_bucket_type = self.env['bucket.type'].sudo().search([('is_vendor', '=', True)])
            if fetch_product_vendor:
                self.bucket_type_id = vendor_bucket_type.id
                self.prod_remaining_budget_vendor_id = fetch_product_vendor.partner_id.id
                self.assignable_status = 'assigned'
            else:
                self.bucket_type_id = vendor_bucket_type.id
                self.assignable_status = 'assignable_at_inv'


    
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
                self.prod_remaining_budget_vendor_id = False or None
                self.prod_remaining_budget_assigned_user_id = False or None
                # self.assignable_status = False
                fetch_product_vendor = self.env['product.supplierinfo'].sudo().search(
                    [('product_tmpl_id', '=', self.product_id.id)], limit=1, order="id desc", )

                if not fetch_product_vendor:
                    self.assignable_status = 'assignable_at_inv'
                else:
                    print("else fetch_product_vendor",fetch_product_vendor.partner_id.name)
                    self.prod_remaining_budget_vendor_id = fetch_product_vendor.partner_id.id
                    self.assignable_status = 'assigned'
            else:
                self.is_vendor = False
                self.prod_remaining_budget_vendor_id = False or None
                self.prod_remaining_budget_assigned_user_id = False or None
                self.assignable_status = 'assignable_at_inv'


        else:
            self.is_vendor = False
            self.prod_remaining_budget_vendor_id = False or None
            self.prod_remaining_budget_assigned_user_id = False or None
            self.assignable_status = False
            
            
    @api.onchange('assignable_status')
    def _onchange_assignable_status(self):
        if self.assignable_status or self.assignable_status == False:
            if self.assignable_status != 'assigned':
                self.prod_remaining_budget_vendor_id = False or None
                self.prod_remaining_budget_assigned_user_id = False or None
            else:

                fetch_product_vendor = self.env['product.supplierinfo'].sudo().search(
                    [('product_tmpl_id', '=', self.product_id.id)], limit=1, order="id desc", )
                if not fetch_product_vendor:
                    if self.bucket_type_id.is_vendor:
                        self.assignable_status = 'assignable_at_inv'
                else:
                    if self.bucket_type_id.is_vendor:
                        self.prod_remaining_budget_vendor_id = fetch_product_vendor.partner_id.id
                    self.assignable_status = 'assigned'
            
            
            
            
    @api.onchange('prod_remaining_budget_vendor_id')
    def _onchange_prod_remaining_budget_vendor_id(self):
        if self.prod_remaining_budget_vendor_id:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))
            

    @api.onchange('prod_remaining_budget_assigned_user_id')
    def _onchange_prod_remaining_budget_assigned_user_id(self):
        if self.prod_remaining_budget_assigned_user_id:
            if not self.assignable_status:
                raise UserError(_('1st select the Assignable status'))


    
class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"



    def unlink(self):
        product_template_id = self.env['product.template'].sudo().search([('id','=',self.product_tmpl_id.id)],limit=1)

        res = super(ProductSupplierinfo, self).unlink()

        seller_id = self.env['product.supplierinfo'].sudo().search([('product_tmpl_id','=',product_template_id.id)],order="id desc",limit=1)
        if seller_id.partner_id:
            product_in_all_fixed_line = self.env['product.budget.fixed'].sudo().search(
                [('product_id', '=', product_template_id.id), ('is_vendor', '=', True),
                 ('assignable_status', '=', 'assigned')])
            product_in_all_allocate_line = self.env['product.budget.allocate'].sudo().search(
                [('product_id', '=', product_template_id.id), ('is_vendor', '=', True),
                 ('assignable_status', '=', 'assigned')])

            for fixed_lines in product_in_all_fixed_line:
                fixed_lines.prod_fix_vendor_id = seller_id.partner_id.id
            for allocate_lines in product_in_all_allocate_line:
                allocate_lines.prod_remaining_budget_vendor_id = seller_id.partner_id.id
        else:
            print("inside delete all vendors in supplier")
            product_in_all_fixed_line = self.env['product.budget.fixed'].sudo().search(
                [('product_id', '=', product_template_id.id), ('is_vendor', '=', True),
                 ('assignable_status', '=', 'assigned')])
            product_in_all_allocate_line = self.env['product.budget.allocate'].sudo().search(
                [('product_id', '=', product_template_id.id), ('is_vendor', '=', True),
                 ('assignable_status', '=', 'assigned')])
            vendor_bucket_type = self.env['bucket.type'].sudo().search([('is_vendor', '=', True)])

            for fixed_lines in product_in_all_fixed_line:
                fixed_lines.prod_fix_vendor_id = ''
                fixed_lines.bucket_type_id = vendor_bucket_type.id
                fixed_lines.assignable_status = 'assignable_at_inv'
            for allocate_lines in product_in_all_allocate_line:
                allocate_lines.prod_remaining_budget_vendor_id = ''
                allocate_lines.bucket_type_id = vendor_bucket_type.id
                allocate_lines.assignable_status = 'assignable_at_inv'

        return res
    
    
    def write(self, vals):
        res = super(ProductSupplierinfo,self).write(vals)
        all_lines = self.env['product.supplierinfo'].sudo().search([('product_tmpl_id','=',self.product_tmpl_id._origin.id)],order='id desc',limit=1)
        print("RRRRRRRRRRRR",all_lines)
        if all_lines.partner_id:
            product_in_all_fixed_line = self.env['product.budget.fixed'].sudo().search(
                [('product_id', '=', self.product_tmpl_id._origin.id), ('is_vendor', '=', True),
                 ('assignable_status', '=', 'assigned')])
            product_in_all_allocate_line = self.env['product.budget.allocate'].sudo().search(
                [('product_id', '=', self.product_tmpl_id._origin.id), ('is_vendor', '=', True),
                 ('assignable_status', '=', 'assigned')])

            for fixed_lines in product_in_all_fixed_line:
                fixed_lines.prod_fix_vendor_id = all_lines.partner_id.id
            for allocate_lines in product_in_all_allocate_line:
                allocate_lines.prod_remaining_budget_vendor_id = all_lines.partner_id.id
        return res


    @api.model_create_multi
    def create(self, vals_list):
        res = super(ProductSupplierinfo,self).create(vals_list)
        for rec in res:
            if rec.partner_id:
                product_in_all_fixed_line = self.env['product.budget.fixed'].sudo().search(
                    [('product_id', '=', rec.product_tmpl_id.id), ('is_vendor', '=', True),
                     ])
                product_in_all_allocate_line = self.env['product.budget.allocate'].sudo().search(
                    [('product_id', '=', rec.product_tmpl_id.id), ('is_vendor', '=', True),
                     ])
                for fixed_lines in product_in_all_fixed_line:
                    if fixed_lines.assignable_status == 'assigned':
                        fixed_lines.prod_fix_vendor_id = rec.partner_id.id
                    elif fixed_lines.assignable_status == 'assignable_at_inv':
                        fixed_lines.prod_fix_vendor_id = rec.partner_id.id
                        fixed_lines.assignable_status = 'assigned'
                for allocate_lines in product_in_all_allocate_line:
                    if allocate_lines.assignable_status == 'assigned':
                        allocate_lines.prod_remaining_budget_vendor_id = rec.partner_id.id
                    elif allocate_lines.assignable_status == 'assignable_at_inv':
                        allocate_lines.prod_remaining_budget_vendor_id = rec.partner_id.id
                        allocate_lines.assignable_status = 'assigned'
        return res
    
    
    
    
    