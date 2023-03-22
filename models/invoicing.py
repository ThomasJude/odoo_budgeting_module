from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    inv_budget_line = fields.One2many('invoice.budget.line', 'prod_inv_id', 'Budget Info')
    product_remaining_budget_line = fields.One2many('product.budget.remaining', 'prod_remaining_id', 'Product Remaining Budget')
    
    @api.constrains("invoice_line_ids","invoice_line_ids.product_id")
    def fetch_fixed_budget_product_data(self):
        for rec in self:
            if rec.invoice_line_ids:
                for inv_line in rec.invoice_line_ids:
                    if inv_line.product_id and inv_line.product_id.product_tmpl_id and inv_line.product_id.product_fixed_budget_line:
                        for fix_budget_line in inv_line.product_id.product_fixed_budget_line:
                            budget_data= self.env['invoice.budget.line'].sudo().create({
                                                                                        'product_id_budget':fix_budget_line.product_id.id,
                                                                                        'name':fix_budget_line.name,
                                                                                        'prod_inv_id':rec.id,
                                                                                        'bucket_type_id':fix_budget_line.bucket_type_id.id,
                                                                                        'assignable_status':fix_budget_line.assignable_status,
                                                                                        'amount':fix_budget_line.amount,
                                                                                        'bucket_user':fix_budget_line.bucket_user,
                                                                                        'budget_inv_vendor_ids': [(6,0, fix_budget_line.prod_fix_vendor_ids.ids)] or [],
                                                                                        'budget_user_ids':[(6,0, fix_budget_line.prod_fix_assigned_user_ids.ids)] or [],
                                                                                        'prod_priority':fix_budget_line.prod_priority
                                                                                        })
                            
                            
                    if inv_line.product_id and inv_line.product_id.product_tmpl_id and inv_line.product_id.product_allocate_budget_line:
                        for allocate_budget_line in inv_line.product_id.product_allocate_budget_line:
                            remaining_budget_data= self.env['product.budget.remaining'].sudo().create({
                                                                                        'product_id_budget':allocate_budget_line.product_id.id,
                                                                                        'name':allocate_budget_line.name,
                                                                                        'prod_remaining_id':rec.id,
                                                                                        'bucket_type_id':allocate_budget_line.bucket_type_id.id,
                                                                                        'assignable_status':allocate_budget_line.assignable_status,
                                                                                        'bucket_user':allocate_budget_line.bucket_user,
                                                                                        'budget_inv_remaining_vendor_ids': [(6,0, allocate_budget_line.prod_remaining_budget_vendor_ids.ids)] or [],
                                                                                        'budget_remaining_user_ids':[(6,0, allocate_budget_line.prod_remaining_budget_assigned_user_ids.ids)] or [],
                                                                                        'allocate_percent':allocate_budget_line.allocate_percent,
                                                                                        'amount':allocate_budget_line.allocate_percent
                                                                                        })
         
         
    def action_post(self):
        res = super(AccountMove, self).action_post()
        priority_list = []
        bucket_type_list = set()

        if self.inv_budget_line:
            for inv_budget in self.inv_budget_line: 
                if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user=='vendor' and not inv_budget.budget_inv_vendor_ids:
                    raise UserError(_("Please assign vendors in budgeting tab"))
                if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user!='vendor' and not inv_budget.budget_user_ids:
                    raise UserError(_("Please assign Users in budgeting tab"))

            for inv_fix_budget in self.inv_budget_line:
                priority_list.append(inv_fix_budget.prod_priority)
                bucket_type_list.add(inv_fix_budget.bucket_type_id)
            priority_list.sort()
            for priority in priority_list:
                for buget_inv_line in self.inv_budget_line:
                    if priority == buget_inv_line.prod_priority:
                        fixed_bucket = self.env['bucket'].sudo().search([('bucket_type_id','=',buget_inv_line.bucket_type_id.id),('bucket_status','=','invoiced')])
                        fixed_bucket.bucket_amount += buget_inv_line.amount

        if self.product_remaining_budget_line:
            for budget_remaining_line in self.product_remaining_budget_line:
                bucket_type_list.add(budget_remaining_line.bucket_type_id)
                remaining_bucket = self.env['bucket'].sudo().search(
                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                remaining_bucket.bucket_amount += budget_remaining_line.amount

            for bucket_type_id in bucket_type_list:
                existing_bucket_dashboard = self.env['bucket.dashboard'].sudo().search([('bucket_type_id','=',bucket_type_id.id)])
                if not existing_bucket_dashboard:
                    self.env['bucket.dashboard'].sudo().create({
                        'bucket_type_id': bucket_type_id.id,
                        'bucket_inv_ids': [(4, self.id, 0)]
                    })
                else:
                    existing_bucket_dashboard.bucket_inv_ids= [(4, self.id, 0)]
        return res
    
    
         
    
    # def action_post(self):
    #     res = super(AccountMove, self).action_post()
    #     if self.inv_budget_line:
    #         for inv_budget in self.inv_budget_line: 
    #             if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user=='vendor' and not inv_budget.budget_inv_vendor_ids:
    #                 raise UserError(_("Please assign vendors in budgeting tab"))
    #             if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user!='vendor' and not inv_budget.budget_user_ids:
    #                 raise UserError(_("Please assign Users in budgeting tab"))
    #     return res



class InvoiceBudgetLine(models.Model):
    _name = "invoice.budget.line"

    name = fields.Text(string='Description', readonly=False)
    product_id_budget = fields.Many2one('product.template', 'Product')
    prod_inv_id = fields.Many2one('account.move', 'Prod Invoice Id')
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    budget_inv_vendor_ids = fields.Many2many(
        'res.partner', 'prod_inv_budget_vendor', 'prod_inv_budget_id', 'vendor_id',
        string='Vendors Name', copy=False)
    budget_user_ids = fields.Many2many('res.users', 'prod_inv_budget_user', 'prod_inv_budget_usr_id', 'usr_id',string="Users Name",copy=False)
    amount = fields.Float("Amount")
    assignable_status = fields.Selection([('assigned', 'Assigned'),
                                          ('unassigned', 'Unassigned'),
                                          ('assignable_at_inv', 'Assignable At Time of Invoice')
                                          ], "Assignable Status")
    bucket_user= fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    prod_priority = fields.Integer('Priority')
    invoiced = fields.Boolean('Invoiced')
    released = fields.Boolean('Released')
    amount_residual = fields.Float('Amount Due')


                    
class ProductBudgetRemaining(models.Model):
    _name = "product.budget.remaining"

    name = fields.Text(string='Description', readonly=False)
    product_id_budget = fields.Many2one('product.template', 'Product', index='btree_not_null')
    prod_remaining_id = fields.Many2one('account.move', 'Prod Allocate')
    allocate_percent = fields.Integer("%", default=0)
    assignable_status = fields.Selection([('assigned', 'Assigned'),
                                          ('unassigned', 'Unassigned'),
                                          ('assignable_at_inv', 'Assignable At Time of Invoice')
                                          ], "Assignable Status")
    bucket_user= fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    budget_inv_remaining_vendor_ids = fields.Many2many(
        'res.partner', 'prod_inv_remaining_budget_vendor', 'prod_inv_remaining_budget_id', 'vendor_id',
        string='Vendors Name', copy=False)
    budget_remaining_user_ids = fields.Many2many('res.users', 'prod_inv_remaining_budget_user', 'prod_inv_remaining_budget_usr_id', 'usr_id',string="Users Name",copy=False)
    
    
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    amount = fields.Float("amount")
    invoiced = fields.Boolean('Invoiced')
    released = fields.Boolean('Released')
    amount_residual = fields.Float('Amount Due')
    
    
class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        res = super(AccountPaymentRegister,self).action_create_payments()
        invoice_amount = self.env['account.move'].sudo().search([('id', '=', self.line_ids.move_id.id)])
        if invoice_amount.amount_total == self.amount:
            if self.line_ids.move_id.inv_budget_line:
                priority_list = []
                for inv_fix_budget in self.line_ids.move_id.inv_budget_line:
                    priority_list.append(inv_fix_budget.prod_priority)
                priority_list.sort()
                for priority in priority_list:
                    for buget_inv_line in self.line_ids.move_id.inv_budget_line:
                        if priority == buget_inv_line.prod_priority:
                            invoices_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                            invoices_bucket.bucket_amount -= buget_inv_line.amount
                            released_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])
                            released_bucket.bucket_amount += buget_inv_line.amount
                            buget_inv_line.released = True

            if self.line_ids.move_id.product_remaining_budget_line:
                for budget_remaining_line in self.line_ids.move_id.product_remaining_budget_line:
                    invoiced_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                    invoiced_bucket.bucket_amount -= budget_remaining_line.amount
                    released_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                         ('bucket_status', '=', 'released')])
                    released_bucket.bucket_amount += budget_remaining_line.amount
                    budget_remaining_line.released = True
        elif invoice_amount.amount_total > self.amount:
            pass
        return res






