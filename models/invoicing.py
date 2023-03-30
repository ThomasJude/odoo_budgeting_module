from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    inv_budget_line = fields.One2many('invoice.budget.line', 'prod_inv_id', 'Budget Info')
    product_remaining_budget_line = fields.One2many('product.budget.remaining', 'prod_remaining_id', 'Product Remaining Budget')
    previous_released_amount = fields.Float('Previous Released')
    
    
    @api.onchange("invoice_line_ids","invoice_line_ids.product_id")
    def _onchange_fetch_fixed_budget_product_data(self):
        print ("11111111111111111111111")
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
                                                                                        # 'budget_inv_vendor_ids': [(6,0, fix_budget_line.prod_fix_vendor_ids.ids)] or [],
                                                                                        'budget_inv_vendor_id': fix_budget_line.prod_fix_vendor_id.id,
                                                                                        # 'budget_user_ids':[(6,0, fix_budget_line.prod_fix_assigned_user_ids.ids)] or [],
                                                                                        'budget_user_id': fix_budget_line.prod_fix_assigned_user_id.id,
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
                                                                                        # 'budget_inv_remaining_vendor_ids': [(6,0, allocate_budget_line.prod_remaining_budget_vendor_ids.ids)] or [],
                                                                                        'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
                                                                                        # 'budget_remaining_user_ids':[(6,0, allocate_budget_line.prod_remaining_budget_assigned_user_ids.ids)] or [],
                                                                                        'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
                                                                                        'allocate_percent':allocate_budget_line.allocate_percent,
                                                                                        'amount':allocate_budget_line.amount
                                                                                        })
    
    # @api.constrains("invoice_line_ids","invoice_line_ids.product_id")
    # def fetch_fixed_budget_product_data(self):
    #     print ("11111111111111111111111")
    #     for rec in self:
    #         if rec.invoice_line_ids:
    #             for inv_line in rec.invoice_line_ids:
    #                 if inv_line.product_id and inv_line.product_id.product_tmpl_id and inv_line.product_id.product_fixed_budget_line:
    #                     for fix_budget_line in inv_line.product_id.product_fixed_budget_line:
    #                         budget_data= self.env['invoice.budget.line'].sudo().create({
    #                                                                                     'product_id_budget':fix_budget_line.product_id.id,
    #                                                                                     'name':fix_budget_line.name,
    #                                                                                     'prod_inv_id':rec.id,
    #                                                                                     'bucket_type_id':fix_budget_line.bucket_type_id.id,
    #                                                                                     'assignable_status':fix_budget_line.assignable_status,
    #                                                                                     'amount':fix_budget_line.amount,
    #                                                                                     'bucket_user':fix_budget_line.bucket_user,
    #                                                                                     # 'budget_inv_vendor_ids': [(6,0, fix_budget_line.prod_fix_vendor_ids.ids)] or [],
    #                                                                                     'budget_inv_vendor_id': fix_budget_line.prod_fix_vendor_id.id,
    #                                                                                     # 'budget_user_ids':[(6,0, fix_budget_line.prod_fix_assigned_user_ids.ids)] or [],
    #                                                                                     'budget_user_id': fix_budget_line.prod_fix_assigned_user_id.id,
    #                                                                                     'prod_priority':fix_budget_line.prod_priority
    #                                                                                     })
    #
    #
    #                 if inv_line.product_id and inv_line.product_id.product_tmpl_id and inv_line.product_id.product_allocate_budget_line:
    #                     for allocate_budget_line in inv_line.product_id.product_allocate_budget_line:
    #                         remaining_budget_data= self.env['product.budget.remaining'].sudo().create({
    #                                                                                     'product_id_budget':allocate_budget_line.product_id.id,
    #                                                                                     'name':allocate_budget_line.name,
    #                                                                                     'prod_remaining_id':rec.id,
    #                                                                                     'bucket_type_id':allocate_budget_line.bucket_type_id.id,
    #                                                                                     'assignable_status':allocate_budget_line.assignable_status,
    #                                                                                     'bucket_user':allocate_budget_line.bucket_user,
    #                                                                                     # 'budget_inv_remaining_vendor_ids': [(6,0, allocate_budget_line.prod_remaining_budget_vendor_ids.ids)] or [],
    #                                                                                     'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
    #                                                                                     # 'budget_remaining_user_ids':[(6,0, allocate_budget_line.prod_remaining_budget_assigned_user_ids.ids)] or [],
    #                                                                                     'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
    #                                                                                     'allocate_percent':allocate_budget_line.allocate_percent,
    #                                                                                     'amount':allocate_budget_line.amount
    #                                                                                     })
         
         
    def action_post(self):
        res = super(AccountMove, self).action_post()
        priority_list = []
        bucket_type_list = set()
        assigned_vendor_lst=[]
        assigned_user_lst = []
        if self.inv_budget_line:
            for inv_budget in self.inv_budget_line: 
                # if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user=='vendor' and not inv_budget.budget_inv_vendor_ids:
                if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user=='vendor' and not inv_budget.budget_inv_vendor_id:
                    raise UserError(_("Please assign vendors in budgeting tab"))
                # if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user!='vendor' and not inv_budget.budget_user_ids:
                if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user!='vendor' and not inv_budget.budget_user_id:
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
                        fixed_bucket_vendor_lst=[]
                        fixed_bucket_user_lst=[]

                        if fixed_bucket.vendor_line:
                            for fixed_vendr in fixed_bucket.vendor_line:
                                fixed_bucket_vendor_lst.append(fixed_vendr.vendor_id.id)

                        if fixed_bucket.user_line:
                            for fixed_user in fixed_bucket.user_line:
                                fixed_bucket_user_lst.append(fixed_user.user_id.id)
                        # if buget_inv_line.budget_inv_vendor_ids:
                        #     for vendr_id in buget_inv_line.budget_inv_vendor_ids:
                        #         if vendr_id.id not in fixed_bucket_vendor_lst:
                        #             assigned_vendor_lst.append(vendr_id.id)
                        if buget_inv_line.budget_inv_vendor_id:
                            for vendr_id in buget_inv_line.budget_inv_vendor_id:
                                if vendr_id.id not in fixed_bucket_vendor_lst:
                                    assigned_vendor_lst.append(vendr_id.id)
                        if buget_inv_line.budget_user_id:
                            for user_id in buget_inv_line.budget_user_id:
                                if user_id.id not in fixed_bucket_user_lst:
                                    user_inv_bucket = self.env['bucket'].sudo().search([('bucket_type_id','=',buget_inv_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                                    existing_rec = self.env['user.line'].sudo().search([('user_line_bucket_id','=',user_inv_bucket.id),('user_id','=', user_id.id)])
                                    if not existing_rec:
                                        user_bucket_line = self.env['user.line'].sudo().create(
                                            {'user_line_bucket_id': user_inv_bucket.id,
                                             'user_id': user_id.id})
                                    # assigned_user_lst.append(user_id.id)



        if self.product_remaining_budget_line:
            for budget_remaining_line in self.product_remaining_budget_line:
                bucket_type_list.add(budget_remaining_line.bucket_type_id)
                remaining_bucket = self.env['bucket'].sudo().search(
                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                remaining_bucket.bucket_amount += budget_remaining_line.amount
                
                remaining_bucket_vendor_lst=[]
                remaining_bucket_user_lst=[]
                if remaining_bucket.vendor_line:
                    for remaining_vendr in remaining_bucket.vendor_line:
                        remaining_bucket_vendor_lst.append(remaining_vendr.id)

                if remaining_bucket.user_line:
                    for remaining_user in remaining_bucket.user_line:
                        remaining_bucket_user_lst.append(remaining_user.id)
                
                # if budget_remaining_line.budget_inv_remaining_vendor_ids:
                #     for rem_vendr_id in budget_remaining_line.budget_inv_remaining_vendor_ids:
                #         if rem_vendr_id.id not in remaining_bucket_vendor_lst:
                #             assigned_vendor_lst.append(rem_vendr_id.id)
                if budget_remaining_line.budget_inv_remaining_vendor_id:
                    for rem_vendr_id in budget_remaining_line.budget_inv_remaining_vendor_id:
                        if rem_vendr_id.id not in remaining_bucket_vendor_lst:
                            assigned_vendor_lst.append(rem_vendr_id.id)

                if budget_remaining_line.budget_remaining_user_id:
                    for rem_user_id in budget_remaining_line.budget_remaining_user_id:
                        if rem_user_id.id not in remaining_bucket_user_lst:
                            user_inv_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'invoiced')])
                            existing_rec = self.env['user.line'].sudo().search(
                                [('user_line_bucket_id', '=', user_inv_bucket.id), ('user_id', '=', rem_user_id.id)])
                            if not existing_rec:
                                user_bucket_line = self.env['user.line'].sudo().create(
                                    {'user_line_bucket_id': user_inv_bucket.id,
                                     'user_id': rem_user_id.id})
                            # assigned_user_lst.append(rem_user_id.id)

            for bucket_type_id in bucket_type_list:
                existing_bucket_dashboard = self.env['bucket.dashboard'].sudo().search([('bucket_type_id','=',bucket_type_id.id)])
                if not existing_bucket_dashboard:
                    self.env['bucket.dashboard'].sudo().create({
                        'bucket_type_id': bucket_type_id.id,
                        'bucket_inv_ids': [(4, self.id, 0)]
                    })
                else:
                    existing_bucket_dashboard.bucket_inv_ids= [(4, self.id, 0)]
                    
        assigned_vendr_set= set(assigned_vendor_lst)
        final_vendor_lst= list(assigned_vendr_set)

        assigned_user_set = set(assigned_user_lst)
        final_user_lst = list(assigned_user_set)

        vendor_bucket_type_id=self.env['bucket.type'].sudo().search([('user_type','=','vendor')],limit=1)
        vendor_inv_bucket = self.env['bucket'].sudo().search([('bucket_type_id', '=', vendor_bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
        for final_vendor in final_vendor_lst:
            final_vendor_id= self.env['res.partner'].browse(final_vendor)
            # vendor_bucket_line= self.env['vendor.line'].sudo().create({'vendor_line_bucket_id':vendor_inv_bucket.id,'vendor_id':final_vendor_id.id})
            existing_vendor = self.env['vendor.line'].sudo().search([("vendor_id", '=', final_vendor_id.id)])
            if not existing_vendor:
                vendor_bucket_line = self.env['vendor.line'].sudo().create(
                    {'vendor_line_bucket_id': vendor_inv_bucket.id, 'vendor_id': final_vendor_id.id})



        return res
    




class InvoiceBudgetLine(models.Model):
    _name = "invoice.budget.line"

    name = fields.Text(string='Description', readonly=False)
    product_id_budget = fields.Many2one('product.template', 'Product')
    prod_inv_id = fields.Many2one('account.move', 'Prod Invoice Id')
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    # budget_inv_vendor_ids = fields.Many2many(
    #     'res.partner', 'prod_inv_budget_vendor', 'prod_inv_budget_id', 'vendor_id',
    #     string='Vendors Name', copy=False)
    budget_inv_vendor_id = fields.Many2one('res.partner', string="Vendors Name", copy=False)
    # budget_user_ids = fields.Many2many('res.users', 'prod_inv_budget_user', 'prod_inv_budget_usr_id', 'usr_id',string="Users Name",copy=False)
    budget_user_id = fields.Many2one('res.users', string="Users Name")
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
    # budget_inv_remaining_vendor_ids = fields.Many2many(
    #     'res.partner', 'prod_inv_remaining_budget_vendor', 'prod_inv_remaining_budget_id', 'vendor_id',
    #     string='Vendors Name', copy=False)
    budget_inv_remaining_vendor_id = fields.Many2one('res.partner', string="Vendors Name", copy=False)
    # budget_remaining_user_ids = fields.Many2many('res.users', 'prod_inv_remaining_budget_user', 'prod_inv_remaining_budget_usr_id', 'usr_id',string="Users Name",copy=False)
    budget_remaining_user_id = fields.Many2one('res.users', string="Users Name", copy=False)

    
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    amount = fields.Float("amount")
    invoiced = fields.Boolean('Invoiced')
    released = fields.Boolean('Released')
    amount_residual = fields.Float('Amount Due')
    
    
class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    
    
    def action_create_payments(self):
        res = super(AccountPaymentRegister,self).action_create_payments()
        # assigned_vendor_lst = []
        invoice_amount = self.env['account.move'].sudo().search([('id', '=', self.line_ids.move_id.id)])
        total_released_amount = self.amount
        self.line_ids.move_id.previous_released_amount += self.amount
        if invoice_amount.amount_total == self.amount and invoice_amount.payment_state == "paid" :
            if self.line_ids.move_id.inv_budget_line:
                priority_list = []
                for inv_fix_budget in self.line_ids.move_id.inv_budget_line:
                    priority_list.append(inv_fix_budget.prod_priority)
                priority_list.sort()
                for priority in priority_list:
                    for buget_inv_line in self.line_ids.move_id.inv_budget_line:
                        if priority == buget_inv_line.prod_priority and not buget_inv_line.released:
                            invoices_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                            invoices_bucket.bucket_amount = invoices_bucket.bucket_amount - buget_inv_line.amount
                            released_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])
                            released_bucket.bucket_amount = released_bucket.bucket_amount+buget_inv_line.amount
                            buget_inv_line.released = True
                            # ////////////////////////////////
                            vendor_released_bucket = self.env['bucket'].sudo().search([('bucket_type_id','=',buget_inv_line.bucket_type_id.id),('bucket_status','=','released')])
                            if buget_inv_line.budget_inv_vendor_id:
                                existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search([('vendor_id','=',buget_inv_line.budget_inv_vendor_id.id)])
                                if not existing_vendor_rel_line:
                                    self.env['vendor.line.released'].sudo().create({'vendor_id':buget_inv_line.budget_inv_vendor_id.id,'vendor_line_released_bucket_id':vendor_released_bucket.id})
                            elif buget_inv_line.budget_user_id:
                                existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                    [('user_id', '=', buget_inv_line.budget_user_id.id),('user_line_released_bucket_id','=',vendor_released_bucket.id)])
                                if not existing_user_rel_line:
                                    self.env['user.line.released'].sudo().create(
                                        {'user_id': buget_inv_line.budget_user_id.id,
                                         'user_line_released_bucket_id': vendor_released_bucket.id})
                            # vendor_bill = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',buget_inv_line.prod_inv_id.name),('vendor_id','=',buget_inv_line.budget_inv_vendor_id.id)])
                            # vendor_bill.released = True
                            # user_bill = self.env['user.invoice.detail'].sudo().search(
                            #     [('invoice_name', '=', buget_inv_line.prod_inv_id.name),
                            #      ('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                            # vendor_bill.released = True
                            # print("wWWWWWWWDddddddddddddd",vendor_bill.released)

            if self.line_ids.move_id.product_remaining_budget_line:

                for budget_remaining_line in self.line_ids.move_id.product_remaining_budget_line:
                    if not budget_remaining_line.released:
                        invoiced_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                        invoiced_bucket.bucket_amount -= budget_remaining_line.amount
                        released_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        released_bucket.bucket_amount += budget_remaining_line.amount
                        budget_remaining_line.released = True

                        # //////////////////////////

                        vendor_released_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        if budget_remaining_line.budget_inv_remaining_vendor_id:
                            existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                            if not existing_vendor_rel_line:
                                self.env['vendor.line.released'].sudo().create(
                                    {'vendor_id': buget_inv_line.budget_inv_remaining_vendor_id.id,
                                     'vendor_line_released_bucket_id': vendor_released_bucket.id})
                        elif budget_remaining_line.budget_remaining_user_id:
                            existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                [('user_id', '=', budget_remaining_line.budget_remaining_user_id.id),('user_line_released_bucket_id','=',vendor_released_bucket.id)])
                            if not existing_user_rel_line:
                                self.env['user.line.released'].sudo().create(
                                    {'user_id': budget_remaining_line.budget_remaining_user_id.id,
                                     'user_line_released_bucket_id': vendor_released_bucket.id})

                        # user_bill = self.env['user.invoice.detail'].sudo().search(
                        #     [('invoice_name', '=', budget_remaining_line.prod_remaining_id.name),
                        #      ('user_id', '=', budget_remaining_line.budget_remaining_user_id.id)])
                        # vendor_bill.released = True
        elif invoice_amount.amount_total > self.amount and invoice_amount.payment_state == "partial":
            if self.line_ids.move_id.inv_budget_line:
                priority_list = []
                for inv_fix_budget in self.line_ids.move_id.inv_budget_line:
                    priority_list.append(inv_fix_budget.prod_priority)
                priority_list.sort()
                for priority in priority_list:
                    for buget_inv_line in self.line_ids.move_id.inv_budget_line:
                        if priority == buget_inv_line.prod_priority and total_released_amount != 0 and not buget_inv_line.released:
                            if buget_inv_line.amount_residual == 0.0:
                                
                                if total_released_amount >= buget_inv_line.amount:
                                    print("WQQQQQQQQQQQQQQQQQQQQQ")
                                    total_released_amount = total_released_amount - buget_inv_line.amount
                                    buget_inv_line.released = True

                                    invoices_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'invoiced')])
                                    invoices_bucket.bucket_amount -= buget_inv_line.amount

                                    released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    released_bucket.bucket_amount += buget_inv_line.amount
                                    ############################################################

                                    vendor_released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    if buget_inv_line.budget_inv_vendor_id:
                                        existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                            [('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                                        if not existing_vendor_rel_line:
                                            self.env['vendor.line.released'].sudo().create(
                                                {'vendor_id': buget_inv_line.budget_inv_vendor_id.id,
                                                 'vendor_line_released_bucket_id': vendor_released_bucket.id})
                                    elif buget_inv_line.budget_user_id:
                                        existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                            [('user_id', '=', buget_inv_line.budget_user_id.id),
                                             ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                                        if not existing_user_rel_line:
                                            self.env['user.line.released'].sudo().create(
                                                {'user_id': buget_inv_line.budget_user_id.id,
                                                 'user_line_released_bucket_id': vendor_released_bucket.id})

                                    ##############################################################3
                                else:
                                    print("WQQQQQQQQQQQQQQQQQQQQQ 1111")
                                    buget_inv_line.amount_residual = buget_inv_line.amount - total_released_amount
                                    invoices_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'invoiced')])
                                    invoices_bucket.bucket_amount -= total_released_amount

                                    released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    released_bucket.bucket_amount += total_released_amount
                                    total_released_amount = buget_inv_line.amount - total_released_amount

                                    ############################################################

                                    vendor_released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    if buget_inv_line.budget_inv_vendor_id:
                                        existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                            [('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                                        if not existing_vendor_rel_line:
                                            self.env['vendor.line.released'].sudo().create(
                                                {'vendor_id': buget_inv_line.budget_inv_vendor_id.id,
                                                 'vendor_line_released_bucket_id': vendor_released_bucket.id})
                                    elif buget_inv_line.budget_user_id:
                                        existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                            [('user_id', '=', buget_inv_line.budget_user_id.id),
                                             ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                                        if not existing_user_rel_line:
                                            self.env['user.line.released'].sudo().create(
                                                {'user_id': buget_inv_line.budget_user_id.id,
                                                 'user_line_released_bucket_id': vendor_released_bucket.id})

                                    ##############################################################3
                                    if buget_inv_line.amount_residual != 0.0 :
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= buget_inv_line.amount_residual:

                                    total_released_amount = total_released_amount - buget_inv_line.amount_residual
                                    buget_inv_line.released = True
                                    invoices_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'invoiced')])
                                    invoices_bucket.bucket_amount -= buget_inv_line.amount_residual

                                    released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    released_bucket.bucket_amount += buget_inv_line.amount_residual
                                    buget_inv_line.amount_residual = 0.0

                                    ############################################################

                                    vendor_released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    if buget_inv_line.budget_inv_vendor_id:
                                        existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                            [('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                                        if not existing_vendor_rel_line:
                                            self.env['vendor.line.released'].sudo().create(
                                                {'vendor_id': buget_inv_line.budget_inv_vendor_id.id,
                                                 'vendor_line_released_bucket_id': vendor_released_bucket.id})
                                    elif buget_inv_line.budget_user_id:
                                        existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                            [('user_id', '=', buget_inv_line.budget_user_id.id),
                                             ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                                        if not existing_user_rel_line:
                                            self.env['user.line.released'].sudo().create(
                                                {'user_id': buget_inv_line.budget_user_id.id,
                                                 'user_line_released_bucket_id': vendor_released_bucket.id})

                                    ##############################################################3



                                else:
                                    buget_inv_line.amount_residual = buget_inv_line.amount - total_released_amount
                                    invoices_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'invoiced')])
                                    invoices_bucket.bucket_amount -= total_released_amount

                                    released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    released_bucket.bucket_amount += total_released_amount

                                    ############################################################

                                    vendor_released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    if buget_inv_line.budget_inv_vendor_id:
                                        existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                            [('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                                        if not existing_vendor_rel_line:
                                            self.env['vendor.line.released'].sudo().create(
                                                {'vendor_id': buget_inv_line.budget_inv_vendor_id.id,
                                                 'vendor_line_released_bucket_id': vendor_released_bucket.id})
                                    elif buget_inv_line.budget_user_id:
                                        existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                            [('user_id', '=', buget_inv_line.budget_user_id.id),
                                             ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                                        if not existing_user_rel_line:
                                            self.env['user.line.released'].sudo().create(
                                                {'user_id': buget_inv_line.budget_user_id.id,
                                                 'user_line_released_bucket_id': vendor_released_bucket.id})

                                    ##############################################################3

                                    if buget_inv_line.amount_residual != 0.0:
                                        total_released_amount = 0


                        elif priority == buget_inv_line.prod_priority and total_released_amount == 0 and not buget_inv_line.released:
                            buget_inv_line.amount_residual = buget_inv_line.amount
            line_amount_released = []
            for buget_inv_line in self.line_ids.move_id.inv_budget_line:
                if buget_inv_line.released:
                    line_amount_released.append(buget_inv_line.released)
            if self.line_ids.move_id.product_remaining_budget_line and buget_inv_line.released and len(self.line_ids.move_id.inv_budget_line) == len(line_amount_released):
                for budget_remaining_line in self.line_ids.move_id.product_remaining_budget_line:
                    if total_released_amount != 0 and not budget_remaining_line.released:
                        if budget_remaining_line.amount_residual == 0.0:
                            if total_released_amount >= budget_remaining_line.amount:
                                total_released_amount = total_released_amount - budget_remaining_line.amount
                                budget_remaining_line.released = True
                                invoiced_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                                invoiced_bucket.bucket_amount -= budget_remaining_line.amount
                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount += budget_remaining_line.amount

                                ############################################################3

                                vendor_released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                if budget_remaining_line.budget_inv_remaining_vendor_id:
                                    existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                        [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if not existing_vendor_rel_line:
                                        self.env['vendor.line.released'].sudo().create(
                                            {'vendor_id': budget_remaining_line.budget_inv_remaining_vendor_id.id,
                                             'vendor_line_released_bucket_id': vendor_released_bucket.id})
                                elif budget_remaining_line.budget_remaining_user_id:
                                    existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                        [('user_id', '=', budget_remaining_line.budget_remaining_user_id.id),
                                         ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                                    if not existing_user_rel_line:
                                        self.env['user.line.released'].sudo().create(
                                            {'user_id': budget_remaining_line.budget_remaining_user_id.id,
                                             'user_line_released_bucket_id': vendor_released_bucket.id})

                                #############################################################3
                            else:
                                budget_remaining_line.amount_residual = budget_remaining_line.amount - total_released_amount
                                invoiced_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                                invoiced_bucket.bucket_amount -= total_released_amount
                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount += total_released_amount

                                ############################################################3

                                vendor_released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                if budget_remaining_line.budget_inv_remaining_vendor_id:
                                    existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                        [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if not existing_vendor_rel_line:
                                        self.env['vendor.line.released'].sudo().create(
                                            {'vendor_id': budget_remaining_line.budget_inv_remaining_vendor_id.id,
                                             'vendor_line_released_bucket_id': vendor_released_bucket.id})
                                elif budget_remaining_line.budget_remaining_user_id:
                                    existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                        [('user_id', '=', budget_remaining_line.budget_remaining_user_id.id),
                                         ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                                    if not existing_user_rel_line:
                                        self.env['user.line.released'].sudo().create(
                                            {'user_id': budget_remaining_line.budget_remaining_user_id.id,
                                             'user_line_released_bucket_id': vendor_released_bucket.id})

                                #############################################################3



                                if budget_remaining_line.amount_residual != 0.0:
                                    total_released_amount = 0


                        else:
                            if total_released_amount >= budget_remaining_line.amount_residual:
                                total_released_amount = total_released_amount - budget_remaining_line.amount_residual
                                invoiced_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'invoiced')])
                                invoiced_bucket.bucket_amount -= budget_remaining_line.amount_residual
                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount += budget_remaining_line.amount_residual
                                budget_remaining_line.amount_residual = 0.0
                                # buget_inv_line.amount_residual = 0
                                budget_remaining_line.released = True

                                ############################################################3

                                vendor_released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                if budget_remaining_line.budget_inv_remaining_vendor_id:
                                    existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                        [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if not existing_vendor_rel_line:
                                        self.env['vendor.line.released'].sudo().create(
                                            {'vendor_id': budget_remaining_line.budget_inv_remaining_vendor_id.id,
                                             'vendor_line_released_bucket_id': vendor_released_bucket.id})
                                elif budget_remaining_line.budget_remaining_user_id:
                                    existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                        [('user_id', '=', budget_remaining_line.budget_remaining_user_id.id),
                                         ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                                    if not existing_user_rel_line:
                                        self.env['user.line.released'].sudo().create(
                                            {'user_id': budget_remaining_line.budget_remaining_user_id.id,
                                             'user_line_released_bucket_id': vendor_released_bucket.id})

                                #############################################################3



                            else:
                                budget_remaining_line.amount_residual = budget_remaining_line.amount_residual - total_released_amount
                                invoiced_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'invoiced')])
                                invoiced_bucket.bucket_amount -= total_released_amount
                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount += total_released_amount

                                ############################################################3

                                vendor_released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                if budget_remaining_line.budget_inv_remaining_vendor_id:
                                    existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                        [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if not existing_vendor_rel_line:
                                        self.env['vendor.line.released'].sudo().create(
                                            {'vendor_id': budget_remaining_line.budget_inv_remaining_vendor_id.id,
                                             'vendor_line_released_bucket_id': vendor_released_bucket.id})
                                elif budget_remaining_line.budget_remaining_user_id:
                                    existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                        [('user_id', '=', budget_remaining_line.budget_remaining_user_id.id),
                                         ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                                    if not existing_user_rel_line:
                                        self.env['user.line.released'].sudo().create(
                                            {'user_id': budget_remaining_line.budget_remaining_user_id.id,
                                             'user_line_released_bucket_id': vendor_released_bucket.id})

                                #############################################################3


                                if budget_remaining_line.amount_residual != 0.0:
                                    total_released_amount = 0
                    elif total_released_amount == 0.0 and not budget_remaining_line.released:
                        budget_remaining_line.amount_residual = budget_remaining_line.amount
        else:
            if self.line_ids.move_id.product_remaining_budget_line:

                for budget_remaining_line in self.line_ids.move_id.product_remaining_budget_line:
                    if not budget_remaining_line.released:
                        invoiced_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                        invoiced_bucket.bucket_amount -= budget_remaining_line.amount_residual
                        released_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        released_bucket.bucket_amount += budget_remaining_line.amount_residual
                        budget_remaining_line.released = True
                        budget_remaining_line.amount_residual = 0.0

                        ############################################################3

                        vendor_released_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        if budget_remaining_line.budget_inv_remaining_vendor_id:
                            existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                            if not existing_vendor_rel_line:
                                self.env['vendor.line.released'].sudo().create(
                                    {'vendor_id': budget_remaining_line.budget_inv_remaining_vendor_id.id,
                                     'vendor_line_released_bucket_id': vendor_released_bucket.id})
                        elif budget_remaining_line.budget_remaining_user_id:
                            existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                [('user_id', '=', budget_remaining_line.budget_remaining_user_id.id),
                                 ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                            if not existing_user_rel_line:
                                self.env['user.line.released'].sudo().create(
                                    {'user_id': budget_remaining_line.budget_remaining_user_id.id,
                                     'user_line_released_bucket_id': vendor_released_bucket.id})

                        #############################################################3

        return res
    



