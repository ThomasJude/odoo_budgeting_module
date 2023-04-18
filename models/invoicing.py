from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    inv_budget_line = fields.One2many('invoice.budget.line', 'prod_inv_id', 'Budget Info')
    product_remaining_budget_line = fields.One2many('product.budget.remaining', 'prod_remaining_id', 'Product Remaining Budget')
    previous_released_amount = fields.Float('Previous Released')
    bill_bucket_id= fields.Many2one('bucket','Bucket')
    # bill_bucket_amount = fields.Float('Bill Bucket Amount ')
    bill_bucket_amount = fields.Float(string='Bill Bucket Amount', compute='_compute_bill_bucket_amount')
    
    @api.depends('bill_bucket_id')
    def _compute_bill_bucket_amount(self):
        self.bill_bucket_amount=0.0
        if self.bill_bucket_id:
            self.bill_bucket_amount = self.bill_bucket_id.bucket_amount
    
    
    # @api.onchange('bill_bucket_id')
    # def bill_bucket_amount_val(self):
    #     if self.bill_bucket_id:
    #         self.bill_bucket_amount= self.bill_bucket_id.bucket_amount
    
    
    

    def button_draft(self):
        res = super(AccountMove,self).button_draft()
        if self.move_type == 'out_invoice':
            if self.inv_budget_line:
                for buget_inv_line in self.inv_budget_line:
                    if not buget_inv_line.released and buget_inv_line.check_invoice_posted:
    
                        # --------------------------------------
                        # buget_inv_line invoiced checkbox true
                        # ----------------------------------------
    
                        fixed_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                             ('bucket_status', '=', 'invoiced')])
                        fixed_bucket.bucket_amount -= buget_inv_line.amount
                        if fixed_bucket.vendor_line:
                            for vendor_line in fixed_bucket.vendor_line:
                                if vendor_line.vendor_id.id == buget_inv_line.budget_inv_vendor_id.id:
                                    existing_rec = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',self.id),('bucket_type_id','=',buget_inv_line.bucket_type_id.id),('vendor_id','=',buget_inv_line.budget_inv_vendor_id.id)])
                                    if existing_rec:
                                        existing_rec.unlink()
                                    cr = self.env.cr
                                    cr.execute(
                                        "SELECT id FROM invoice_budget_line where check_invoice_posted = '%s' and budget_inv_vendor_id = '%s' and bucket_type_id = '%s' and prod_inv_id != '%s'",
                                        (True, buget_inv_line.budget_inv_vendor_id.id,
                                         buget_inv_line.bucket_type_id.id, self.id))
                                    existing_vendor_ids_in_inv_line = cr.fetchall()
                                    if not existing_vendor_ids_in_inv_line:
                                        vendor_line.unlink()
                                    buget_inv_line.check_invoice_posted = False
                        else:
                            for user_line in fixed_bucket.user_line:
                                if user_line.user_id.id == buget_inv_line.budget_user_id.id:
                                    existing_rec = self.env['user.invoice.detail'].sudo().search([('invoice_name','=',self.id),('bucket_type_id','=',buget_inv_line.bucket_type_id.id),('user_id','=',buget_inv_line.budget_user_id.id)])
                                    if existing_rec:
                                        for del_rec in existing_rec:
                                            del_rec.unlink()
                                    cr = self.env.cr
                                    cr.execute(
                                        "SELECT id FROM invoice_budget_line where check_invoice_posted = '%s' and budget_user_id = '%s' and bucket_type_id = '%s' and prod_inv_id != '%s'",
                                        (True, buget_inv_line.budget_user_id.id, buget_inv_line.bucket_type_id.id, self.id))
                                    survey_user_ids = cr.fetchall()
                                    if not survey_user_ids:
                                        user_line.unlink()
                                    buget_inv_line.check_invoice_posted = False
                                    
                        # buget_inv_line.check_invoice_posted = False
            if self.product_remaining_budget_line:
                for budget_remaining_line in self.product_remaining_budget_line:
                    if not budget_remaining_line.released and budget_remaining_line.check_invoice_posted:
    
                        # --------------------------------------
                        # budget_remaining_line invoiced checkbox true
                        # ----------------------------------------
                        remaining_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                        remaining_bucket.bucket_amount -= budget_remaining_line.amount
                        if remaining_bucket.vendor_line:
                            for vendor_line in remaining_bucket.vendor_line:
                                if vendor_line.vendor_id.id == budget_remaining_line.budget_inv_remaining_vendor_id.id:
                                    existing_rec = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',self.id),('bucket_type_id','=',budget_remaining_line.bucket_type_id.id),('vendor_id','=',budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if existing_rec:
                                        existing_rec.unlink()
                                    cr = self.env.cr
                                    cr.execute(
                                        "SELECT id FROM product_budget_remaining where check_invoice_posted = '%s' and budget_inv_remaining_vendor_id = '%s' and bucket_type_id = '%s' and prod_remaining_id != '%s'",
                                        (True, budget_remaining_line.budget_inv_remaining_vendor_id.id,
                                         budget_remaining_line.bucket_type_id.id, self.id))
                                    existing_rec_of_rem_vendr = cr.fetchall()
                                    if not existing_rec_of_rem_vendr:
                                        vendor_line.unlink()
                                    budget_remaining_line.check_invoice_posted = False
                        else:
                            for user_line in remaining_bucket.user_line:
                                if user_line.user_id.id == budget_remaining_line.budget_remaining_user_id.id:
                                    existing_rec = self.env['user.invoice.detail'].sudo().search([('invoice_name','=',self.id),('bucket_type_id','=',budget_remaining_line.bucket_type_id.id),('user_id','=',budget_remaining_line.budget_remaining_user_id.id)])
                                    if existing_rec:
                                        existing_rec.unlink()
                                    cr = self.env.cr
                                    cr.execute(
                                        "SELECT id FROM product_budget_remaining where check_invoice_posted = '%s' and budget_remaining_user_id = '%s' and bucket_type_id = '%s' and prod_remaining_id != '%s'",
                                        (True, budget_remaining_line.budget_remaining_user_id.id,
                                         budget_remaining_line.bucket_type_id.id, self.id))
                                    existing_user_ids_in_rem = cr.fetchall()
                                    if not existing_user_ids_in_rem:
    
                                        user_line.unlink()
                                    budget_remaining_line.check_invoice_posted = False
                        # budget_remaining_line.check_invoice_posted = False

        return res

    @api.model_create_multi
    def create(self, vals_list):
        rec = super(AccountMove,self).create(vals_list)
        if rec.move_type == 'out_invoice':
            if rec.invoice_line_ids:
                for inv_line in rec.invoice_line_ids:
                    print("SSSSSSS",inv_line.quantity)

                    if inv_line.product_id and inv_line.product_id.product_tmpl_id and inv_line.product_id.product_fixed_budget_line:
                        for fix_budget_line in inv_line.product_id.product_fixed_budget_line:
                            budget_data= self.env['invoice.budget.line'].sudo().create({
                                                                                        'product_id_budget':fix_budget_line.product_id.id,
                                                                                        'name':fix_budget_line.name,
                                                                                        'prod_inv_id':rec.id,
                                                                                        'account_move_line_id':inv_line.id,
                                                                                        'bucket_type_id':fix_budget_line.bucket_type_id.id,
                                                                                        'assignable_status':fix_budget_line.assignable_status,
                                                                                        'amount':fix_budget_line.amount*inv_line.quantity,
                                                                                        'is_vendor':fix_budget_line.is_vendor,
                                                                                        # 'bucket_user':fix_budget_line.bucket_user,
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
                                                                                        'account_move_line_id': inv_line.id,
                                                                                        'bucket_type_id':allocate_budget_line.bucket_type_id.id,
                                                                                        'assignable_status':allocate_budget_line.assignable_status,
                                                                                        'is_vendor':fix_budget_line.is_vendor,
                                                                                        # 'bucket_user':allocate_budget_line.bucket_user,
                                                                                        # 'budget_inv_remaining_vendor_ids': [(6,0, allocate_budget_line.prod_remaining_budget_vendor_ids.ids)] or [],
                                                                                        'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
                                                                                        # 'budget_remaining_user_ids':[(6,0, allocate_budget_line.prod_remaining_budget_assigned_user_ids.ids)] or [],
                                                                                        'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
                                                                                        'allocate_percent':allocate_budget_line.allocate_percent,
                                                                                        'amount':allocate_budget_line.amount*inv_line.quantity
                                                                                        })

        return rec


    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if self.move_type == 'out_invoice':
            if vals.get('invoice_line_ids'):
                for addedline,addedlineid in zip(vals.get('invoice_line_ids'),self.invoice_line_ids):
                    print("WFXXXXXX",addedline,addedlineid)
                    if addedline[1] != addedlineid.id:
    
                        if addedline[2] and addedline[2].get('product_id'):
                            product_id = self.env['product.product'].sudo().search([('id','=',addedline[2]['product_id'])])
                            if addedline[2].get('quantity'):
                                quantity = addedline[2].get('quantity')
                            else:
                                quantity = 1
                            if product_id and product_id.product_tmpl_id and product_id.product_fixed_budget_line:
                                for fix_budget_line in product_id.product_fixed_budget_line:
                                    budget_data = self.env['invoice.budget.line'].sudo().create({
                                        'product_id_budget': fix_budget_line.product_id.id,
                                        'name': fix_budget_line.name,
                                        'prod_inv_id': self.id,
                                        'account_move_line_id': addedlineid.id,
                                        'bucket_type_id': fix_budget_line.bucket_type_id.id,
                                        'assignable_status': fix_budget_line.assignable_status,
                                        'amount': fix_budget_line.amount * quantity,
                                        'is_vendor':fix_budget_line.is_vendor,
                                        # 'bucket_user': fix_budget_line.bucket_user,
                                        # 'budget_inv_vendor_ids': [(6,0, fix_budget_line.prod_fix_vendor_ids.ids)] or [],
                                        'budget_inv_vendor_id': fix_budget_line.prod_fix_vendor_id.id,
                                        # 'budget_user_ids':[(6,0, fix_budget_line.prod_fix_assigned_user_ids.ids)] or [],
                                        'budget_user_id': fix_budget_line.prod_fix_assigned_user_id.id,
                                        'prod_priority': fix_budget_line.prod_priority
                                    })
    
                            if product_id and product_id.product_tmpl_id and product_id.product_allocate_budget_line:
                                for allocate_budget_line in product_id.product_allocate_budget_line:
                                    remaining_budget_data = self.env['product.budget.remaining'].sudo().create({
                                        'product_id_budget': allocate_budget_line.product_id.id,
                                        'name': allocate_budget_line.name,
                                        'prod_remaining_id': self.id,
                                        'account_move_line_id': addedlineid.id,
                                        'bucket_type_id': allocate_budget_line.bucket_type_id.id,
                                        'assignable_status': allocate_budget_line.assignable_status,
                                        # 'bucket_user': allocate_budget_line.bucket_user,
                                        'is_vendor':allocate_budget_line.is_vendor,
                                        # 'budget_inv_remaining_vendor_ids': [(6,0, allocate_budget_line.prod_remaining_budget_vendor_ids.ids)] or [],
                                        'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
                                        # 'budget_remaining_user_ids':[(6,0, allocate_budget_line.prod_remaining_budget_assigned_user_ids.ids)] or [],
                                        'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
                                        'allocate_percent': allocate_budget_line.allocate_percent,
                                        'amount': allocate_budget_line.amount * quantity
                                    })
                    else:
                        if addedline[1] and addedline[2]:
                            if addedline[2].get('quantity'):
                                quantity = addedline[2].get('quantity')
                            else:
                                quantity = 1
                            move_line = self.env['account.move.line'].sudo().search([('id','=',addedline[1])])
                            get_move_line_product = self.env['product.product'].sudo().search([('id','=',move_line.product_id.id)])
                            inv_buget_line_product_link_recrd = self.env['invoice.budget.line'].sudo().search([('account_move_line_id','=',addedline[1])])
                            remaining_budget_line_product_link_recrd = self.env['product.budget.remaining'].sudo().search([('account_move_line_id','=',addedline[1])])
    
                            if inv_buget_line_product_link_recrd:
                                for records in inv_buget_line_product_link_recrd:
                                    for fix_budget_line in get_move_line_product.product_fixed_budget_line:
                                        if fix_budget_line.prod_priority == records.prod_priority:
                                            records.amount = fix_budget_line.amount * quantity
                                    # records.amount = records.amount * addedline[2]['quantity']
                            if remaining_budget_line_product_link_recrd:
                                for recrd in remaining_budget_line_product_link_recrd:
                                    for allocate_budget_line in get_move_line_product.product_allocate_budget_line:
                                        if allocate_budget_line.allocate_percent == recrd.allocate_percent and allocate_budget_line.bucket_type_id.id == recrd.bucket_type_id.id:
                                            recrd.amount = allocate_budget_line.amount * quantity
    
                            # recrd.amount = recrd.amount * addedline[2]['quantity']
        return res

         
         
    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.move_type== 'out_invoice':
            priority_list = []
            bucket_type_list = set()
            assigned_vendor_lst=[]
            assigned_user_lst = []
            if self.inv_budget_line:
                for inv_budget in self.inv_budget_line: 
                    # if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user=='vendor' and not inv_budget.budget_inv_vendor_ids:
                    if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.is_vendor== True and not inv_budget.budget_inv_vendor_id:
                        raise UserError(_("Please assign vendors in budgeting tab"))
                    # if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.bucket_user!='vendor' and not inv_budget.budget_user_ids:
                    if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget.is_vendor!= True and not inv_budget.budget_user_id:
                        raise UserError(_("Please assign Users in budgeting tab"))
    
                for inv_fix_budget in self.inv_budget_line:
                    priority_list.append(inv_fix_budget.prod_priority)
                    bucket_type_list.add(inv_fix_budget.bucket_type_id)
                remove_repitetion_priority_list = set(priority_list)
                final_priority_list = sorted(remove_repitetion_priority_list)
    
                for priority in final_priority_list:
                    for buget_inv_line in self.inv_budget_line:
                        if priority == buget_inv_line.prod_priority:
                            fixed_bucket = self.env['bucket'].sudo().search([('bucket_type_id','=',buget_inv_line.bucket_type_id.id),('bucket_status','=','invoiced')])
                            fixed_bucket.bucket_amount += buget_inv_line.amount
    
                            buget_inv_line.check_invoice_posted = True
    
                            fixed_bucket_vendor_lst=[]
                            fixed_bucket_user_lst=[]
    
                            if fixed_bucket.vendor_line:
                                for fixed_vendr in fixed_bucket.vendor_line:
                                    fixed_bucket_vendor_lst.append(fixed_vendr.vendor_id.id)
    
                            if fixed_bucket.user_line:
                                for fixed_user in fixed_bucket.user_line:
                                    fixed_bucket_user_lst.append(fixed_user.user_id.id)

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
    
    
            if self.product_remaining_budget_line:
                for rem_budget in self.product_remaining_budget_line: 
                    if rem_budget.assignable_status == 'assignable_at_inv' and rem_budget.is_vendor== True and not rem_budget.budget_inv_remaining_vendor_id:
                        raise UserError(_("Please assign vendors in budgeting tab"))
                    if rem_budget.assignable_status == 'assignable_at_inv' and rem_budget.is_vendor!= True and not rem_budget.budget_remaining_user_id:
                        raise UserError(_("Please assign Users in budgeting tab"))
                
                for budget_remaining_line in self.product_remaining_budget_line:
                    bucket_type_list.add(budget_remaining_line.bucket_type_id)
                    remaining_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
                    remaining_bucket.bucket_amount += budget_remaining_line.amount
    
                    print("budget_remaining_line", budget_remaining_line.check_invoice_posted)
                    budget_remaining_line.check_invoice_posted = True
                    print("budget_remaining_line 2", budget_remaining_line.check_invoice_posted)
                    #
                    remaining_bucket_vendor_lst=[]
                    remaining_bucket_user_lst=[]
                    if remaining_bucket.vendor_line:
                        for remaining_vendr in remaining_bucket.vendor_line:
                            remaining_bucket_vendor_lst.append(remaining_vendr.id)
    
                    if remaining_bucket.user_line:
                        for remaining_user in remaining_bucket.user_line:
                            remaining_bucket_user_lst.append(remaining_user.id)
                    
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
    
            vendor_bucket_type_id=self.env['bucket.type'].sudo().search([('is_vendor','=',True)],limit=1)
            vendor_inv_bucket = self.env['bucket'].sudo().search([('bucket_type_id', '=', vendor_bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
            for final_vendor in final_vendor_lst:
                final_vendor_id= self.env['res.partner'].browse(final_vendor)
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
    account_move_line_id = fields.Many2one('account.move.line','Prod Move Line')
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    budget_inv_vendor_id = fields.Many2one('res.partner', string="Vendors Name", copy=False)
    budget_user_id = fields.Many2one('res.users', string="Users Name")
    amount = fields.Float("Amount")
    assignable_status = fields.Selection([('assigned', 'Assigned'),
                                          ('unassigned', 'Unassigned'),
                                          ('assignable_at_inv', 'Assignable At Time of Invoice')
                                          ], "Assignable Status")
    
    is_vendor = fields.Boolean(string='Is Vendor')
    prod_priority = fields.Integer('Priority')
    invoiced = fields.Boolean('Invoiced')
    released = fields.Boolean('Released')
    amount_residual = fields.Float('Amount Due')
    check_invoice_posted = fields.Boolean('check invoice posted')
    item_refunded = fields.Boolean('Refunded')
    refund_residual = fields.Float('Refund Due')


                    
class ProductBudgetRemaining(models.Model):
    _name = "product.budget.remaining"

    name = fields.Text(string='Description', readonly=False)
    product_id_budget = fields.Many2one('product.template', 'Product', index='btree_not_null')
    prod_remaining_id = fields.Many2one('account.move', 'Prod Allocate')
    allocate_percent = fields.Integer("%", default=0)
    account_move_line_id = fields.Many2one('account.move.line','Prod Allocate Move Line')

    assignable_status = fields.Selection([('assigned', 'Assigned'),
                                          ('unassigned', 'Unassigned'),
                                          ('assignable_at_inv', 'Assignable At Time of Invoice')
                                          ], "Assignable Status")
    is_vendor = fields.Boolean(string='Is Vendor')
    # bucket_user= fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    budget_inv_remaining_vendor_id = fields.Many2one('res.partner', string="Vendors Name", copy=False)
    # budget_remaining_user_ids = fields.Many2many('res.users', 'prod_inv_remaining_budget_user', 'prod_inv_remaining_budget_usr_id', 'usr_id',string="Users Name",copy=False)
    budget_remaining_user_id = fields.Many2one('res.users', string="Users Name", copy=False)

    
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    amount = fields.Float("amount")
    invoiced = fields.Boolean('Invoiced')
    released = fields.Boolean('Released')
    amount_residual = fields.Float('Amount Due')
    check_invoice_posted = fields.Boolean('check invoice posted')
    item_refunded = fields.Boolean('Refunded')
    refund_residual = fields.Float('Refund Due')
    
    
class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    
    
    def action_create_payments(self):
        res = super(AccountPaymentRegister,self).action_create_payments()
        invoice_amount = self.env['account.move'].sudo().search([('id', '=', self.line_ids.move_id.id)])
        if invoice_amount.move_type == 'in_invoice':
            total_released_amount = self.amount
            if invoice_amount.bill_bucket_amount < self.amount:
                raise UserError(_('Bucket Amount is less than amount'))
            if invoice_amount.bill_bucket_id:
                invoice_amount.bill_bucket_id.bucket_amount = invoice_amount.bill_bucket_id.bucket_amount - self.amount
            if invoice_amount.amount_total > self.amount and invoice_amount.payment_state == "partial":
                if invoice_amount.invoice_line_ids:
                    for bill_line in invoice_amount.invoice_line_ids:
                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.bill_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                else:
                                    bill_line.bill_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.bill_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.bill_residual_amount = 0.0
                                else:
                                    bill_line.bill_residual_amount = bill_line.bill_residual_amount - total_released_amount
                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_paid:
                            bill_line.bill_residual_amount = bill_line.price_subtotal

            else:
                if invoice_amount.invoice_line_ids:
                    for bill_line in invoice_amount.invoice_line_ids:
                        if not bill_line.is_bill_paid:
                            bill_line.is_bill_paid = True
                            bill_line.bill_residual_amount = 0.0

        
        if invoice_amount.move_type == 'out_invoice':
            total_released_amount = self.amount
            self.line_ids.move_id.previous_released_amount += self.amount
            # print("TOTAL RELEASED AMOUNT",total_released_amount,invoice_amount.amount_residual)
            if invoice_amount.amount_total == self.amount and invoice_amount.payment_state in ("paid","in_payment") :
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
                                    [('user_id', '=', budget_remaining_line.budget_remaining_user_id.id),('user_line_released_bucket_id','=',vendor_released_bucket.id)])
                                if not existing_user_rel_line:
                                    self.env['user.line.released'].sudo().create(
                                        {'user_id': budget_remaining_line.budget_remaining_user_id.id,
                                         'user_line_released_bucket_id': vendor_released_bucket.id})
        
            elif invoice_amount.amount_total > self.amount and invoice_amount.payment_state == "partial":
                if self.line_ids.move_id.inv_budget_line:
                    priority_list = []
                    for inv_fix_budget in self.line_ids.move_id.inv_budget_line:
                        priority_list.append(inv_fix_budget.prod_priority)
                    final_priority_list = sorted(set(priority_list))
    
                    for priority in final_priority_list:
                        for buget_inv_line in self.line_ids.move_id.inv_budget_line:
    
                            if priority == buget_inv_line.prod_priority and total_released_amount != 0.0 and not buget_inv_line.released:
                                if buget_inv_line.amount_residual == 0.0:
                                    if total_released_amount >= buget_inv_line.amount:
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
                                        print("WWWWWQQQQQQQQQ1111",buget_inv_line.amount_residual)
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
                                        buget_inv_line.amount_residual = buget_inv_line.amount_residual - total_released_amount
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
    
    
                if self.line_ids.move_id.product_remaining_budget_line  and len(self.line_ids.move_id.inv_budget_line) == len(line_amount_released):
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
                if self.line_ids.move_id.inv_budget_line:
    
                    for inv_budget_line in self.line_ids.move_id.inv_budget_line:
                        if not inv_budget_line.released:
                            invoiced_bucket_inv = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'invoiced')])
                            invoiced_bucket_inv.bucket_amount -= inv_budget_line.amount_residual
                            released_bucket_inv = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])
    
                            released_bucket_inv.bucket_amount += inv_budget_line.amount_residual
                            inv_budget_line.released = True
                            inv_budget_line.amount_residual = 0.0
    
                            ############################################################
    
                            vendor_released_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])
                            if inv_budget_line.budget_inv_vendor_id:
                                existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                    [('vendor_id', '=', inv_budget_line.budget_inv_vendor_id.id)])
                                if not existing_vendor_rel_line:
                                    self.env['vendor.line.released'].sudo().create(
                                        {'vendor_id': inv_budget_line.budget_inv_vendor_id.id,
                                         'vendor_line_released_bucket_id': vendor_released_bucket.id})
                            elif inv_budget_line.budget_user_id:
                                existing_user_rel_line = self.env['user.line.released'].sudo().search(
                                    [('user_id', '=', inv_budget_line.budget_user_id.id),
                                     ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                                if not existing_user_rel_line:
                                    self.env['user.line.released'].sudo().create(
                                        {'user_id': inv_budget_line.budget_user_id.id,
                                         'user_line_released_bucket_id': vendor_released_bucket.id})
    
                            ##############################################################3



                if self.line_ids.move_id.product_remaining_budget_line and invoice_amount.amount_residual != 0.0:
                    print("inside if amount residual is great than 0")
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
    
                else:

                    for budget_remaining_line in self.line_ids.move_id.product_remaining_budget_line:
                        if not budget_remaining_line.released and budget_remaining_line.amount_residual !=0.0:
                            print("inside else of amount residual is great than 0 11", invoice_amount.amount_residual)

                            invoiced_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'invoiced')])
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
                            # reeee
                        elif not budget_remaining_line.released and budget_remaining_line.amount_residual == 0.0:
                            print("inside else of amount residual is great than 0 22", invoice_amount.amount_residual)
                            # devvv
                            invoiced_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'invoiced')])

                            invoiced_bucket.bucket_amount -= budget_remaining_line.amount

                            released_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])

                            released_bucket.bucket_amount += budget_remaining_line.amount
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


        elif invoice_amount.move_type == 'out_refund':
            total_released_amount = self.amount
            if invoice_amount.amount_total == self.amount and invoice_amount.payment_state in ("paid", "in_payment"):
                    if self.line_ids.move_id.reversed_entry_id.invoice_line_ids:
                        for move_line_id in self.line_ids.move_id.reversed_entry_id.invoice_line_ids:
                            if self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                                priority_list = []
                                for inv_fix_budget in self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                                    if move_line_id.id == inv_fix_budget.account_move_line_id.id:
                                        priority_list.append(inv_fix_budget.prod_priority)
                                priority_list.sort()

                                for priority in priority_list:
                                    for buget_inv_line in self.line_ids.move_id.reversed_entry_id.inv_budget_line:

                                        if priority == buget_inv_line.prod_priority and buget_inv_line.released and move_line_id.id == buget_inv_line.account_move_line_id.id and not buget_inv_line.item_refunded:
                                            released_bucket = self.env['bucket'].sudo().search(
                                                [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                                 ('bucket_status', '=', 'released')])
                                            released_bucket.bucket_amount = released_bucket.bucket_amount - buget_inv_line.amount

                                            buget_inv_line.item_refunded = True

                            if self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:

                                for budget_remaining_line in self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
                                    if budget_remaining_line.released and move_line_id.id == budget_remaining_line.account_move_line_id.id and not budget_remaining_line.item_refunded:
                                        released_bucket = self.env['bucket'].sudo().search(
                                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                             ('bucket_status', '=', 'released')])

                                        released_bucket.bucket_amount -= budget_remaining_line.amount

                                        budget_remaining_line.item_refunded = True

            elif invoice_amount.amount_total > self.amount and invoice_amount.payment_state == "partial":
                if self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                    priority_list = []
                    for inv_fix_budget in self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                        priority_list.append(inv_fix_budget.prod_priority)
                    final_priority_list = sorted(set(priority_list))

                    for priority in final_priority_list:
                        for buget_inv_line in self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                            print("CSSSSSSSSSSSS",buget_inv_line.item_refunded)
                            if priority == buget_inv_line.prod_priority and total_released_amount != 0.0 and not buget_inv_line.item_refunded:
                                if buget_inv_line.refund_residual == 0.0:
                                    # print("BBBBBBBBBBBBBBBBBBB", total_released_amount, buget_inv_line.amount)
                                    if total_released_amount >= buget_inv_line.amount:
                                        # print("WQQQQQQQQQQQQQQQQQQQQQ")
                                        total_released_amount = total_released_amount - buget_inv_line.amount
                                        buget_inv_line.item_refunded = True

                                        released_bucket = self.env['bucket'].sudo().search(
                                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                             ('bucket_status', '=', 'released')])
                                        released_bucket.bucket_amount -= buget_inv_line.amount

                                    else:
                                        # print("WQQQQQQQQQQQQQQQQQQQQQ 1111")
                                        buget_inv_line.refund_residual = buget_inv_line.amount - total_released_amount

                                        released_bucket = self.env['bucket'].sudo().search(
                                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                             ('bucket_status', '=', 'released')])
                                        released_bucket.bucket_amount -= total_released_amount
                                        total_released_amount = buget_inv_line.amount - total_released_amount
                                        # print("WWWWWQQQQQQQQQ1111", buget_inv_line.amount_residual)

                                        if buget_inv_line.refund_residual != 0.0:
                                            total_released_amount = 0
                                else:
                                    if total_released_amount >= buget_inv_line.refund_residual:

                                        total_released_amount = total_released_amount - buget_inv_line.refund_residual
                                        buget_inv_line.item_refunded = True


                                        released_bucket = self.env['bucket'].sudo().search(
                                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                             ('bucket_status', '=', 'released')])
                                        released_bucket.bucket_amount -= buget_inv_line.refund_residual
                                        buget_inv_line.refund_residual = 0.0

                                    else:
                                        buget_inv_line.refund_residual = buget_inv_line.refund_residual - total_released_amount

                                        released_bucket = self.env['bucket'].sudo().search(
                                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                             ('bucket_status', '=', 'released')])
                                        released_bucket.bucket_amount -= total_released_amount


                                        if buget_inv_line.refund_residual != 0.0:
                                            total_released_amount = 0


                            elif priority == buget_inv_line.prod_priority and total_released_amount == 0 and not buget_inv_line.item_refunded:
                                buget_inv_line.refund_residual = buget_inv_line.amount
                # pass
                line_amount_released = []
                for buget_inv_line in self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                    if buget_inv_line.item_refunded:
                        line_amount_released.append(buget_inv_line.item_refunded)
                if self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line and len(self.line_ids.move_id.reversed_entry_id.inv_budget_line) == len(line_amount_released):
                    for budget_remaining_line in self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
                        if total_released_amount != 0 and not budget_remaining_line.item_refunded:
                            if budget_remaining_line.refund_residual == 0.0:
                                if total_released_amount >= budget_remaining_line.amount:
                                    total_released_amount = total_released_amount - budget_remaining_line.amount
                                    budget_remaining_line.item_refunded = True

                                    released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    released_bucket.bucket_amount -= budget_remaining_line.amount


                                else:
                                    budget_remaining_line.refund_residual = budget_remaining_line.amount - total_released_amount

                                    released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    released_bucket.bucket_amount -= total_released_amount

                                    if budget_remaining_line.refund_residual != 0.0:
                                        total_released_amount = 0


                            else:
                                if total_released_amount >= budget_remaining_line.refund_residual:
                                    total_released_amount = total_released_amount - budget_remaining_line.refund_residual

                                    released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    released_bucket.bucket_amount -= budget_remaining_line.refund_residual
                                    budget_remaining_line.refund_residual = 0.0
                                    # buget_inv_line.amount_residual = 0
                                    budget_remaining_line.item_refunded = True


                                else:
                                    budget_remaining_line.refund_residual = budget_remaining_line.refund_residual - total_released_amount

                                    released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])
                                    released_bucket.bucket_amount -= total_released_amount

                                    if budget_remaining_line.refund_residual != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0.0 and not budget_remaining_line.item_refunded:
                            budget_remaining_line.refund_residual = budget_remaining_line.amount
                        print("REMAINING LINE", budget_remaining_line.refund_residual)

            else:

                if self.line_ids.move_id.reversed_entry_id.inv_budget_line:

                    for inv_budget_line in self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                        if not inv_budget_line.item_refunded:

                            released_bucket_inv = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])
                            released_bucket_inv.bucket_amount -= inv_budget_line.refund_residual
                            inv_budget_line.item_refunded = True
                            inv_budget_line.refund_residual = 0.0



                if self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line and invoice_amount.reversed_entry_id.amount_residual != 0.0:
                    for budget_remaining_line in self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
                        if not budget_remaining_line.item_refunded:

                            released_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])
                            released_bucket.bucket_amount -= budget_remaining_line.refund_residual
                            budget_remaining_line.item_refunded = True
                            budget_remaining_line.refund_residual = 0.0

                else:

                    for budget_remaining_line in self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
                        if not budget_remaining_line.item_refunded and budget_remaining_line.refund_residual != 0.0:

                            released_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])
                            released_bucket.bucket_amount -= budget_remaining_line.refund_residual
                            budget_remaining_line.item_refunded = True
                            budget_remaining_line.refund_residual = 0.0


                        elif not budget_remaining_line.item_refunded and budget_remaining_line.refund_residual == 0.0:

                            released_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])
                            released_bucket.bucket_amount -= budget_remaining_line.amount
                            budget_remaining_line.item_refunded = True
                            budget_remaining_line.refund_residual = 0.0

        return res
    


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    inv_budget_line = fields.One2many('invoice.budget.line', 'account_move_line_id', 'Budget Info')
    remaining_budget_line = fields.One2many('product.budget.remaining', 'account_move_line_id', 'Budget Info')
    is_bill_paid = fields.Boolean('Paid')
    bill_residual_amount = fields.Float('Due Amount')
    parent_move_type = fields.Selection(related='move_id.move_type', store=True, readonly=True, precompute=True,)

    def unlink(self):
        for rec in self:
            if rec.move_id.move_type == 'out_invoice':
                for record in rec.move_id.inv_budget_line:
                    if record and record.account_move_line_id.id == rec.id:
                        record.unlink()
                for record1 in rec.move_id.product_remaining_budget_line:
                    if record1 and record1.account_move_line_id.id == rec.id:
                        record1.unlink()
        res = super(AccountMoveLine,self).unlink()
        return res

