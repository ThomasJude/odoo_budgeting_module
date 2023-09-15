from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    inv_budget_line = fields.One2many('invoice.budget.line', 'prod_inv_id', 'Budget Info')
    product_remaining_budget_line = fields.One2many('product.budget.remaining', 'prod_remaining_id',
                                                    'Product Remaining Budget')
    previous_released_amount = fields.Float('Previous Released')

    def js_assign_out_invoice_in_payment(self,invoice_amount):

        if invoice_amount.inv_budget_line:
            priority_list = []
            for inv_fix_budget in invoice_amount.inv_budget_line:
                priority_list.append(inv_fix_budget.prod_priority)
            priority_list.sort()
            for priority in priority_list:
                for buget_inv_line in invoice_amount.inv_budget_line:
                    if priority == buget_inv_line.prod_priority and not buget_inv_line.released:
                        invoices_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                             ('bucket_status', '=', 'invoiced')])
                        invoices_bucket.bucket_amount = invoices_bucket.bucket_amount - buget_inv_line.amount
                        released_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        released_bucket.bucket_amount = released_bucket.bucket_amount + buget_inv_line.amount
                        buget_inv_line.released = True
                        # ////////////////////////////////
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
        if invoice_amount.product_remaining_budget_line:

            for budget_remaining_line in invoice_amount.product_remaining_budget_line:
                if not budget_remaining_line.released:
                    invoiced_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                         ('bucket_status', '=', 'invoiced')])
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
                            [('user_id', '=', budget_remaining_line.budget_remaining_user_id.id),
                             ('user_line_released_bucket_id', '=', vendor_released_bucket.id)])
                        if not existing_user_rel_line:
                            self.env['user.line.released'].sudo().create(
                                {'user_id': budget_remaining_line.budget_remaining_user_id.id,
                                 'user_line_released_bucket_id': vendor_released_bucket.id})


    def js_assign_out_invoice_fixed_line_partial_paid(self,invoice_amount,total_released_amount):
        if invoice_amount.inv_budget_line:
            priority_list = []
            for inv_fix_budget in invoice_amount.inv_budget_line:
                priority_list.append(inv_fix_budget.prod_priority)
            final_priority_list = sorted(set(priority_list))

            for priority in final_priority_list:
                for buget_inv_line in invoice_amount.inv_budget_line:

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
                                if buget_inv_line.amount_residual != 0.0:
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

    def js_assign_out_invoice_remaining_line_partial_paid(self,invoice_amount,total_released_amount):
        for budget_remaining_line in invoice_amount.product_remaining_budget_line:
            if total_released_amount != 0 and not budget_remaining_line.released:

                if budget_remaining_line.amount_residual == 0.0:
                    if total_released_amount >= budget_remaining_line.amount:
                        total_released_amount = total_released_amount - budget_remaining_line.amount
                        budget_remaining_line.released = True
                        invoiced_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'invoiced')])
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
                                [('vendor_id', '=',
                                  budget_remaining_line.budget_inv_remaining_vendor_id.id)])
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
                                [('vendor_id', '=',
                                  budget_remaining_line.budget_inv_remaining_vendor_id.id)])
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
                        budget_remaining_line.released = True

                        ############################################################3

                        vendor_released_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        if budget_remaining_line.budget_inv_remaining_vendor_id:
                            existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                [('vendor_id', '=',
                                  budget_remaining_line.budget_inv_remaining_vendor_id.id)])
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
                                [('vendor_id', '=',
                                  budget_remaining_line.budget_inv_remaining_vendor_id.id)])
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

    def js_assign_out_invoice_partial_payment(self,invoice_amount,total_released_amount):

        self.js_assign_out_invoice_fixed_line_partial_paid(invoice_amount,total_released_amount)
        line_amount_released = []
        for buget_inv_line in invoice_amount.inv_budget_line:
            if buget_inv_line.released:
                line_amount_released.append(buget_inv_line.released)

        if invoice_amount.product_remaining_budget_line and len(
                invoice_amount.inv_budget_line) == len(line_amount_released):
            self.js_assign_out_invoice_remaining_line_partial_paid(invoice_amount,total_released_amount)

    def js_assign_out_invoice(self,invoice_amount):
        if invoice_amount.inv_budget_line:

            for inv_budget_line in invoice_amount.inv_budget_line:
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

        if invoice_amount.product_remaining_budget_line and invoice_amount.amount_residual != 0.0:
            for budget_remaining_line in self.product_remaining_budget_line:
                if not budget_remaining_line.released:
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

        else:

            for budget_remaining_line in invoice_amount.product_remaining_budget_line:
                if not budget_remaining_line.released and budget_remaining_line.amount_residual != 0.0:

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
                elif not budget_remaining_line.released and budget_remaining_line.amount_residual == 0.0:
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



    def js_assign_in_invoice_partial_paid(self,invoice_amount,total_released_amount):
        if invoice_amount.invoice_line_ids:
            for bill_line in invoice_amount.invoice_line_ids:

                if not bill_line.is_partial and not bill_line.is_bill_paid:
                    if total_released_amount > bill_line.price_subtotal:
                        bill_line.bucket_ids.bucket_amount -= bill_line.price_subtotal
                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.bill_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.is_partial = True

                                else:
                                    bill_line.bill_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.bill_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.bill_residual_amount = 0.0
                                else:
                                    bill_line.bill_residual_amount = bill_line.bill_residual_amount - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_paid:
                            bill_line.bill_residual_amount = bill_line.price_subtotal
                        total_released_amount -= bill_line.price_subtotal
                    else:
                        bill_line.bucket_ids.bucket_amount -= total_released_amount

                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.bill_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.is_partial = True

                                else:
                                    bill_line.bill_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.bill_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.bill_residual_amount = 0.0
                                else:
                                    bill_line.bill_residual_amount = bill_line.bill_residual_amount - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_paid:
                            bill_line.bill_residual_amount = bill_line.price_subtotal
                elif bill_line.is_partial and not bill_line.is_bill_paid:
                    if bill_line.bill_residual_amount >= total_released_amount:

                        bill_line.bucket_ids.bucket_amount -= total_released_amount

                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.bill_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.is_partial = True

                                else:
                                    bill_line.bill_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.bill_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.bill_residual_amount = 0.0
                                else:
                                    bill_line.bill_residual_amount = bill_line.bill_residual_amount - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_paid:
                            bill_line.bill_residual_amount = bill_line.price_subtotal

                    else:
                        bill_line.bucket_ids.bucket_amount -= bill_line.bill_residual_amount
                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.bill_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.is_partial = True

                                else:
                                    bill_line.bill_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.bill_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.bill_residual_amount = 0.0
                                else:
                                    bill_line.bill_residual_amount = bill_line.bill_residual_amount - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_paid:
                            bill_line.bill_residual_amount = bill_line.price_subtotal

                        total_released_amount = total_released_amount - bill_line.bill_residual_amount


    def js_assign_in_invoice(self,invoice_amount):
        if invoice_amount.invoice_line_ids:
            for bill_line in invoice_amount.invoice_line_ids:

                if not bill_line.bill_residual_amount:

                    if not bill_line.is_bill_paid:
                        if bill_line.bill_residual_amount != 0.0:
                            bill_line.bucket_ids.bucket_amount -= bill_line.bill_residual_amount
                        else:
                            bill_line.bucket_ids.bucket_amount -= bill_line.price_subtotal
                        if bill_line.bucket_ids.bucket_type_id:
                            if not bill_line.is_bill_paid:
                                bill_line.is_bill_paid = True
                                bill_line.is_partial = True

                                bill_line.bill_residual_amount = 0.0

                        else:
                            if not bill_line.is_bill_paid:
                                bill_line.is_bill_paid = True
                                bill_line.is_partial = True

                                bill_line.bill_residual_amount = 0.0
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                else:
                    if not bill_line.is_bill_paid:
                        if bill_line.bill_residual_amount != 0.0:
                            bill_line.bucket_ids.bucket_amount -= bill_line.bill_residual_amount
                        else:
                            bill_line.bucket_ids.bucket_amount -= bill_line.price_unit
                        if bill_line.bucket_ids.bucket_type_id:
                            if not bill_line.is_bill_paid:
                                bill_line.is_bill_paid = True
                                bill_line.bill_residual_amount = 0.0

                        else:
                            if not bill_line.is_bill_paid:
                                bill_line.is_bill_paid = True
                                bill_line.bill_residual_amount = 0.0
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

    def js_assign_out_refund_partial_paid(self,total_released_amount):
        if self.invoice_line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
            for budget_remaining_line in self.invoice_line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
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

        allocate_line_amount_released = []
        for inv_fix_budget in self.invoice_line_ids.move_id.reversed_entry_id.inv_budget_line:
            inv_fix_budget.update({"refund_residual": 0.0})
        for budget_remaining_line in self.invoice_line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
            if budget_remaining_line.item_refunded:
                allocate_line_amount_released.append(budget_remaining_line.item_refunded)
        if self.invoice_line_ids.move_id.reversed_entry_id.inv_budget_line and len(
                self.invoice_line_ids.move_id.reversed_entry_id.product_remaining_budget_line) == len(
            allocate_line_amount_released):
            priority_list = []
            for inv_fix_budget in self.invoice_line_ids.move_id.reversed_entry_id.inv_budget_line:
                priority_list.append(inv_fix_budget.prod_priority)
            final_priority_list = sorted(set(priority_list), reverse=True)
            for priority in final_priority_list:
                for buget_inv_line in self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                    if priority == buget_inv_line.prod_priority and total_released_amount != 0.0 and not buget_inv_line.item_refunded:
                        if buget_inv_line.refund_residual == 0.0:
                            if total_released_amount >= buget_inv_line.amount:
                                total_released_amount = total_released_amount - buget_inv_line.amount
                                buget_inv_line.item_refunded = True

                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount -= buget_inv_line.amount

                            else:
                                buget_inv_line.refund_residual = buget_inv_line.amount - total_released_amount

                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount -= total_released_amount
                                total_released_amount = buget_inv_line.amount - total_released_amount

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


    def js_assign_out_refund_paid(self):
        if self.invoice_line_ids.move_id.reversed_entry_id.invoice_line_ids:
            for move_line_id in self.invoice_line_ids.move_id.reversed_entry_id.invoice_line_ids:
                if self.invoice_line_ids.move_id.reversed_entry_id.product_remaining_budget_line:

                    for budget_remaining_line in self.invoice_line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
                        if budget_remaining_line.released and move_line_id.id == budget_remaining_line.account_move_line_id.id and not budget_remaining_line.item_refunded:
                            if budget_remaining_line.refund_residual == 0.0:
                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount -= budget_remaining_line.amount

                                budget_remaining_line.item_refunded = True
                                budget_remaining_line.refund_residual = 0.0
                            else:
                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])

                                released_bucket.bucket_amount -= budget_remaining_line.refund_residual

                                budget_remaining_line.item_refunded = True
                                budget_remaining_line.refund_residual = 0.0
                allocate_line_amount_released = []
                for budget_remaining_line in self.invoice_line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
                    if budget_remaining_line.item_refunded:
                        allocate_line_amount_released.append(budget_remaining_line.item_refunded)
                if len(self.invoice_line_ids.move_id.reversed_entry_id.product_remaining_budget_line) == len(
                        allocate_line_amount_released):
                    if self.invoice_line_ids.move_id.reversed_entry_id.inv_budget_line:
                        priority_list = []
                        for inv_fix_budget in self.invoice_line_ids.move_id.reversed_entry_id.inv_budget_line:
                            if move_line_id.id == inv_fix_budget.account_move_line_id.id:
                                priority_list.append(inv_fix_budget.prod_priority)
                        priority_list.sort()

                        for priority in priority_list:
                            for buget_inv_line in self.invoice_line_ids.move_id.reversed_entry_id.inv_budget_line:

                                if priority == buget_inv_line.prod_priority and buget_inv_line.released and move_line_id.id == buget_inv_line.account_move_line_id.id and not buget_inv_line.item_refunded:
                                    released_bucket = self.env['bucket'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('bucket_status', '=', 'released')])

                                    released_bucket.bucket_amount = released_bucket.bucket_amount - buget_inv_line.amount

                                    buget_inv_line.item_refunded = True
                                    buget_inv_line.refund_residual = 0.0


    def js_assign_in_refund_partial_paid(self,invoice_amount,total_released_amount):
        if invoice_amount.reversed_entry_id.invoice_line_ids:
            for bill_line in invoice_amount.reversed_entry_id.invoice_line_ids:
                if not bill_line.is_refund_partial and not bill_line.is_bill_refunded:
                    if total_released_amount >= bill_line.price_subtotal:
                        bill_line.bucket_ids.bucket_amount -= bill_line.price_subtotal
                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.refund_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.is_refund_partial = True

                                else:
                                    bill_line.refund_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.refund_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.refund_residual_amount = 0.0
                                else:
                                    bill_line.refund_residual_amount = bill_line.refund_residual_amount - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_refunded:
                            bill_line.refund_residual_amount = bill_line.price_subtotal
                        total_released_amount -= bill_line.price_subtotal
                    else:
                        bill_line.bucket_ids.bucket_amount -= bill_line.price_subtotal - total_released_amount

                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_refunded:
                            if bill_line.refund_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.is_refund_partial = True

                                else:
                                    bill_line.refund_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.refund_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.refund_residual_amount = 0.0
                                else:
                                    bill_line.refund_residual_amount = bill_line.refund_residual_amount - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_refunded:
                            bill_line.refund_residual_amount = bill_line.price_subtotal
                elif bill_line.is_refund_partial and not bill_line.is_bill_refunded:
                    if bill_line.refund_residual_amount >= total_released_amount:

                        bill_line.bucket_ids.bucket_amount -= total_released_amount
                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_refunded:
                            if bill_line.refund_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.is_refund_partial = True

                                else:
                                    bill_line.refund_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.refund_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.refund_residual_amount = 0.0
                                else:
                                    bill_line.refund_residual_amount = bill_line.refund_residual_amount - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_refunded:
                            bill_line.refund_residual_amount = bill_line.price_subtotal

                    else:
                        bill_line.bucket_ids.bucket_amount -= bill_line.price_subtotal - bill_line.refund_residual_amount
                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_refunded:
                            if bill_line.refund_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.is_refund_partial = True

                                else:
                                    bill_line.refund_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.refund_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.refund_residual_amount = 0.0
                                else:
                                    bill_line.refund_residual_amount = bill_line.refund_residual_amount - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_refunded:
                            bill_line.refund_residual_amount = bill_line.price_subtotal

                        total_released_amount = total_released_amount - bill_line.refund_residual_amount


    def js_assign_in_refund_paid(self,invoice_amount):
        if invoice_amount.reversed_entry_id.invoice_line_ids:
            for bill_line in invoice_amount.reversed_entry_id.invoice_line_ids:

                if bill_line.refund_residual_amount == 0.0:

                    if not bill_line.is_bill_refunded:
                        if bill_line.refund_residual_amount != 0.0:
                            bill_line.bucket_ids.bucket_amount -= bill_line.refund_residual_amount
                        else:
                            bill_line.bucket_ids.bucket_amount -= bill_line.price_subtotal
                        if bill_line.bucket_ids.bucket_type_id:
                            if not bill_line.is_bill_refunded:
                                bill_line.is_bill_refunded = True
                                bill_line.is_refund_partial = True

                                bill_line.refund_residual_amount = 0.0

                        else:
                            if not bill_line.is_bill_refunded:
                                bill_line.is_bill_refunded = True
                                bill_line.is_refund_partial = True

                                bill_line.refund_residual_amount = 0.0
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                else:
                    if not bill_line.is_bill_refunded:
                        if bill_line.refund_residual_amount != 0.0:
                            bill_line.bucket_ids.bucket_amount -= bill_line.refund_residual_amount
                        else:
                            bill_line.bucket_ids.bucket_amount -= bill_line.price_unit
                        if bill_line.bucket_ids.bucket_type_id:
                            if not bill_line.is_bill_refunded:
                                bill_line.is_bill_refunded = True
                                bill_line.refund_residual_amount = 0.0

                        else:
                            if not bill_line.is_bill_refunded:
                                bill_line.is_bill_refunded = True
                                bill_line.refund_residual_amount = 0.0
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})




    def js_assign_outstanding_line(self, line_id):
        res = super(AccountMove, self).js_assign_outstanding_line(line_id)
        self.payment_edit_remove_from_released()
        self.payment_edit_add_to_invoiced()
        all_payments = self.env['account.payment'].sudo().search([("ref", '=', self.name)])
        amount_paid = 0
        for payments in all_payments:
            if payments.is_reconciled:
                amount_paid += payments.amount

        invoice_amount = self.env['account.move'].sudo().search([('id', '=', self.id)])
        if invoice_amount.move_type == 'out_invoice':
            total_released_amount = amount_paid
            if invoice_amount.amount_total == amount_paid and invoice_amount.payment_state in ("paid", "in_payment"):
                self.js_assign_out_invoice_in_payment(invoice_amount)
            elif invoice_amount.amount_total > amount_paid and invoice_amount.payment_state == "partial":
                self.js_assign_out_invoice_partial_payment(invoice_amount,total_released_amount)
            else:
                self.js_assign_out_invoice(invoice_amount)

        if invoice_amount.move_type == 'in_invoice':
            total_released_amount = amount_paid
            if invoice_amount.amount_total > amount_paid and invoice_amount.payment_state == "partial":
                self.js_assign_in_invoice_partial_paid(invoice_amount,total_released_amount)
            else:
                self.js_assign_in_invoice(invoice_amount)


        if invoice_amount.move_type == "out_refund":

            all_payments_return = self.env['account.payment'].sudo().search([("ref", 'ilike', f"Reversal of: {self.reversed_entry_id.name}")])

            for payments in all_payments_return:
                if payments.is_reconciled:
                    amount_paid += payments.amount
            total_released_amount = amount_paid

            if invoice_amount.amount_total > amount_paid and invoice_amount.payment_state == "partial":
                self.js_assign_out_refund_partial_paid(total_released_amount)

            else:
                self.js_assign_out_refund_paid()


        if invoice_amount.move_type == "in_refund":
            all_payments_return = self.env['account.payment'].sudo().search([("ref", 'ilike', f"Reversal of: {self.reversed_entry_id.name}")])
            for payments in all_payments_return:
                if payments.is_reconciled:
                    amount_paid += payments.amount
            total_released_amount = amount_paid
            if invoice_amount.amount_total > amount_paid and invoice_amount.payment_state == "partial":
                self.js_assign_in_refund_partial_paid(invoice_amount, total_released_amount)
            else:
                self.js_assign_in_refund_paid(invoice_amount)

        return res


    def payment_edit_out_invoice_remove(self,invoice):
        if invoice:
            if invoice.inv_budget_line:
                for buget_inv_line in invoice.inv_budget_line:
                    if buget_inv_line.released:
                        buget_inv_line.update({"amount_residual": 0.0})

                        fixed_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])

                        fixed_bucket.bucket_amount -= buget_inv_line.amount
                        buget_inv_line.released = False
                        buget_inv_line.check_invoice_posted = False
                        if fixed_bucket.vendor_line_released:
                            for vendor_line in fixed_bucket.vendor_line_released:
                                if vendor_line.vendor_id.id == buget_inv_line.budget_inv_vendor_id.id:
                                    existing_rec = self.env['vendor.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', invoice.id),
                                         ('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                                    if existing_rec:
                                        existing_rec.unlink()
                                    all_existing_rec_of_vendr = self.env['vendor.invoice.detail'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                                    if not all_existing_rec_of_vendr:
                                        vendor_line.unlink()
                        else:
                            for user_line in fixed_bucket.user_line_released.user_id:
                                if user_line.user_id.id == buget_inv_line.budget_user_id.id:
                                    existing_rec = self.env['user.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', invoice.id),
                                         ('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('user_id', '=', buget_inv_line.budget_user_id.id)])
                                    if existing_rec:
                                        existing_rec.unlink()
                                    all_existing_rec_of_user = self.env['user.invoice.detail'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('user_id', '=', buget_inv_line.budget_user_id.id)])
                                    if not all_existing_rec_of_user:
                                        user_line.unlink()
                    elif not buget_inv_line.released:
                        invoiced_fixed_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                             ('bucket_status', '=', 'invoiced')])

                        fixed_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        if buget_inv_line.amount_residual:
                            fixed_bucket.bucket_amount -= buget_inv_line.amount - buget_inv_line.amount_residual

                        if buget_inv_line.amount_residual != 0.0:
                            invoiced_fixed_bucket.bucket_amount -= buget_inv_line.amount_residual
                        else:
                            invoiced_fixed_bucket.bucket_amount -= buget_inv_line.amount

                        buget_inv_line.update({"amount_residual": 0.0})

                        if invoiced_fixed_bucket.vendor_line_released:
                            for vendor_line_invoiced in invoiced_fixed_bucket.vendor_line_released:
                                if vendor_line_invoiced.vendor_id.id == buget_inv_line.budget_inv_vendor_id.id:
                                    existing_rec_invoiced = self.env['vendor.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', invoice.id),
                                         ('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                                    if existing_rec_invoiced:
                                        existing_rec_invoiced.unlink()
                                    all_existing_rec_of_vendr_invoiced = self.env[
                                        'vendor.invoice.detail'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                                    if not all_existing_rec_of_vendr_invoiced:
                                        vendor_line_invoiced.unlink()


                        else:
                            for user_line_invoiced in invoiced_fixed_bucket.user_line_released.user_id:
                                if user_line_invoiced.user_id.id == buget_inv_line.budget_user_id.id:
                                    existing_rec_invoiced = self.env['user.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', invoice.id),
                                         ('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('user_id', '=', buget_inv_line.budget_user_id.id)])
                                    if existing_rec_invoiced:
                                        existing_rec_invoiced.unlink()
                                    all_existing_rec_of_user_invoiced = self.env[
                                        'user.invoice.detail'].sudo().search(
                                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('user_id', '=', buget_inv_line.budget_user_id.id)])
                                    if not all_existing_rec_of_user_invoiced:
                                        user_line_invoiced.unlink()

            if invoice.product_remaining_budget_line:
                for budget_remaining_line in invoice.product_remaining_budget_line:
                    if budget_remaining_line.released:
                        budget_remaining_line.released = False
                        budget_remaining_line.check_invoice_posted = False
                        budget_remaining_line.update({"amount_residual": 0.0})
                        remaining_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])

                        remaining_bucket.bucket_amount -= budget_remaining_line.amount

                        if remaining_bucket.vendor_line_released:
                            for vendor_line in remaining_bucket.vendor_line_released:
                                if vendor_line.vendor_id.id == budget_remaining_line.budget_inv_remaining_vendor_id.id:
                                    existing_rec = self.env['vendor.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', invoice.id),
                                         ('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('vendor_id', '=',
                                          budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if existing_rec:
                                        existing_rec.unlink()
                                    all_existing_rec_of_vendr = self.env['vendor.invoice.detail'].sudo().search(
                                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('vendor_id', '=',
                                          budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if not all_existing_rec_of_vendr:
                                        vendor_line.unlink()

                        else:
                            for user_line in remaining_bucket.user_line_released:
                                if user_line.user_id.id == budget_remaining_line.budget_remaining_user_id.id:
                                    existing_rec = self.env['user.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', invoice.id),
                                         ('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('user_id', '=', budget_remaining_line.budget_remaining_user_id.id)])

                                    if existing_rec:
                                        existing_rec.unlink()
                                    all_existing_rec_of_rem_user = self.env['user.invoice.detail'].sudo().search(
                                        [('bucket_type_id', '=', budget_remaining_line.budget_remaining_user_id.id),
                                         ('user_id', '=', budget_remaining_line.budget_remaining_user_id.id)])
                                    if not all_existing_rec_of_rem_user:
                                        user_line.unlink()
                    elif not budget_remaining_line.released:
                        remaining_bucket_invoiced = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'invoiced')])

                        remaining_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        if budget_remaining_line.amount_residual:
                            remaining_bucket.bucket_amount -= budget_remaining_line.amount - budget_remaining_line.amount_residual

                        if budget_remaining_line.amount_residual != 0.0:
                            remaining_bucket_invoiced.bucket_amount -= budget_remaining_line.amount_residual
                            budget_remaining_line.update({"amount_residual": 0.0})
                        else:
                            remaining_bucket_invoiced.bucket_amount -= budget_remaining_line.amount
                        if remaining_bucket_invoiced.vendor_line_released:
                            for vendor_line_invoiced in remaining_bucket_invoiced.vendor_line_released:
                                if vendor_line_invoiced.vendor_id.id == budget_remaining_line.budget_inv_remaining_vendor_id.id:
                                    existing_rec_invoiced = self.env['vendor.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', invoice.id),
                                         ('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('vendor_id', '=',
                                          budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if existing_rec_invoiced:
                                        existing_rec_invoiced.unlink()
                                    all_existing_rec_of_vendr_invoiced = self.env[
                                        'vendor.invoice.detail'].sudo().search(
                                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('vendor_id', '=',
                                          budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if not all_existing_rec_of_vendr_invoiced:
                                        vendor_line_invoiced.unlink()

                        else:
                            for user_line_invoiced in remaining_bucket_invoiced.user_line_released:
                                if user_line_invoiced.user_id.id == budget_remaining_line.budget_remaining_user_id.id:
                                    existing_rec_invoiced = self.env['user.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', invoice.id),
                                         ('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('user_id', '=', budget_remaining_line.budget_remaining_user_id.id)])

                                    if existing_rec_invoiced:
                                        existing_rec_invoiced.unlink()
                                    all_existing_rec_of_rem_user_invoiced = self.env[
                                        'user.invoice.detail'].sudo().search(
                                        [('bucket_type_id', '=', budget_remaining_line.budget_remaining_user_id.id),
                                         ('user_id', '=', budget_remaining_line.budget_remaining_user_id.id)])
                                    if not all_existing_rec_of_rem_user_invoiced:
                                        user_line_invoiced.unlink()

    def payment_edit_in_invoice_remove(self,invoice):
        if invoice.invoice_line_ids:
            for bill_line in invoice.invoice_line_ids:
                if bill_line.is_partial and not bill_line.is_bill_paid:
                    if bill_line.bill_residual_amount:
                        bill_line.bucket_ids.bucket_amount += bill_line.price_subtotal - bill_line.bill_residual_amount
                        bill_line.is_partial = False
                        bill_line.update({"bill_residual_amount": 0.0})
                else:
                    bill_line.bucket_ids.bucket_amount += bill_line.price_subtotal
                    bill_line.is_partial = False
                    bill_line.is_bill_paid = False

    def payment_edit_out_refund_remove(self,invoice) :
        if invoice.reversed_entry_id.product_remaining_budget_line:
            for budget_remaining_line in invoice.reversed_entry_id.product_remaining_budget_line:
                if budget_remaining_line.item_refunded:
                    budget_remaining_line.item_refunded = False
                    budget_remaining_line.update({"refund_residual": 0.0})
                    remaining_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                         ('bucket_status', '=', 'released')])

                    remaining_bucket.bucket_amount += budget_remaining_line.amount
                elif not budget_remaining_line.item_refunded:

                    remaining_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                         ('bucket_status', '=', 'released')])
                    if budget_remaining_line.refund_residual:
                        remaining_bucket.bucket_amount += budget_remaining_line.amount - budget_remaining_line.refund_residual
                        budget_remaining_line.update({"refund_residual": 0.0})
        if invoice.reversed_entry_id.inv_budget_line:
            for buget_inv_line in invoice.reversed_entry_id.inv_budget_line:
                if buget_inv_line.item_refunded:

                    buget_inv_line.update({"amount_residual": 0.0})

                    fixed_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                         ('bucket_status', '=', 'released')])

                    fixed_bucket.bucket_amount += buget_inv_line.amount
                    buget_inv_line.item_refunded = False
                elif not buget_inv_line.item_refunded:
                    fixed_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                         ('bucket_status', '=', 'released')])
                    if buget_inv_line.amount_residual:
                        fixed_bucket.bucket_amount += buget_inv_line.amount - buget_inv_line.amount_residual
                        buget_inv_line.update({"amount_residual": 0.0})

    def payment_edit_in_refund_remove(self,invoice):
        if invoice.reversed_entry_id.invoice_line_ids:
            for bill_line in invoice.reversed_entry_id.invoice_line_ids:
                if bill_line.is_refund_partial and not bill_line.is_bill_refunded:
                    if bill_line.refund_residual_amount:
                        bill_line.bucket_ids.bucket_amount += bill_line.refund_residual_amount
                        bill_line.is_refund_partial = False
                        bill_line.update({"refund_residual_amount": 0.0})
                else:
                    bill_line.bucket_ids.bucket_amount += bill_line.price_subtotal
                    bill_line.is_refund_partial = False
                    bill_line.is_bill_refunded = False

    def payment_edit_remove_from_released(self):
        invoice = self.env['account.move'].sudo().search([('id', '=', self.id)])
        if invoice.move_type == 'out_invoice':
            self.payment_edit_out_invoice_remove(invoice)
        elif invoice.move_type == 'in_invoice':
            self.payment_edit_in_invoice_remove(invoice)
        elif invoice.move_type == 'out_refund':
            self.payment_edit_out_refund_remove(invoice)
        elif invoice.move_type == "in_refund":
            self.payment_edit_in_refund_remove(invoice)

    def payment_edit_add_to_invoiced(self):
        if self.move_type == 'out_invoice':
            priority_list = []
            bucket_type_list = set()
            assigned_vendor_lst = []
            assigned_user_lst = []
            if self.inv_budget_line:
                for inv_budget in self.inv_budget_line:
                    if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget == True and not inv_budget.budget_inv_vendor_id:
                        raise UserError(_("Please assign vendors in budgeting tab"))
                    if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget != True and not inv_budget.budget_user_id:
                        raise UserError(_("Please assign Users in budgeting tab"))

                for inv_fix_budget in self.inv_budget_line:
                    priority_list.append(inv_fix_budget.prod_priority)
                    bucket_type_list.add(inv_fix_budget.bucket_type_id)
                remove_repitetion_priority_list = set(priority_list)
                final_priority_list = sorted(remove_repitetion_priority_list)

                for priority in final_priority_list:
                    for buget_inv_line in self.inv_budget_line:
                        if priority == buget_inv_line.prod_priority:
                            fixed_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'invoiced')])
                            fixed_bucket.bucket_amount += buget_inv_line.amount

                            buget_inv_line.check_invoice_posted = True

                            fixed_bucket_vendor_lst = []
                            fixed_bucket_user_lst = []

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
                                        user_inv_bucket = self.env['bucket'].sudo().search(
                                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                             ('bucket_status', '=', 'invoiced')])
                                        existing_rec = self.env['user.line'].sudo().search(
                                            [('user_line_bucket_id', '=', user_inv_bucket.id),
                                             ('user_id', '=', user_id.id)])
                                        if not existing_rec:
                                            user_bucket_line = self.env['user.line'].sudo().create(
                                                {'user_line_bucket_id': user_inv_bucket.id,
                                                 'user_id': user_id.id})

            if self.product_remaining_budget_line:
                for rem_budget in self.product_remaining_budget_line:
                    if rem_budget.assignable_status == 'assignable_at_inv' and rem_budget == True and not rem_budget.budget_inv_remaining_vendor_id:
                        raise UserError(_("Please assign vendors in budgeting tab"))
                    if rem_budget.assignable_status == 'assignable_at_inv' and rem_budget != True and not rem_budget.budget_remaining_user_id:
                        raise UserError(_("Please assign Users in budgeting tab"))

                for budget_remaining_line in self.product_remaining_budget_line:
                    bucket_type_list.add(budget_remaining_line.bucket_type_id)
                    remaining_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                         ('bucket_status', '=', 'invoiced')])
                    remaining_bucket.bucket_amount += budget_remaining_line.amount

                    budget_remaining_line.check_invoice_posted = True
                    remaining_bucket_vendor_lst = []
                    remaining_bucket_user_lst = []
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
                                    [('user_line_bucket_id', '=', user_inv_bucket.id),
                                     ('user_id', '=', rem_user_id.id)])
                                if not existing_rec:
                                    user_bucket_line = self.env['user.line'].sudo().create(
                                        {'user_line_bucket_id': user_inv_bucket.id,
                                         'user_id': rem_user_id.id})

                for bucket_type_id in bucket_type_list:
                    existing_bucket_dashboard = self.env['bucket.dashboard'].sudo().search(
                        [('bucket_type_id', '=', bucket_type_id.id)])
                    if not existing_bucket_dashboard:
                        self.env['bucket.dashboard'].sudo().create({
                            'bucket_type_id': bucket_type_id.id,
                            'bucket_inv_ids': [(4, self.id, 0)]
                        })
                    else:
                        existing_bucket_dashboard.bucket_inv_ids = [(4, self.id, 0)]

            assigned_vendr_set = set(assigned_vendor_lst)
            final_vendor_lst = list(assigned_vendr_set)

            assigned_user_set = set(assigned_user_lst)
            final_user_lst = list(assigned_user_set)

            vendor_bucket_type_id = self.env['bucket.type'].sudo().search([], limit=1)
            vendor_inv_bucket = self.env['bucket'].sudo().search(
                [('bucket_type_id', '=', vendor_bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
            for final_vendor in final_vendor_lst:
                final_vendor_id = self.env['res.partner'].browse(final_vendor)
                existing_vendor = self.env['vendor.line'].sudo().search([("vendor_id", '=', final_vendor_id.id)])
                if not existing_vendor:
                    vendor_bucket_line = self.env['vendor.line'].sudo().create(
                        {'vendor_line_bucket_id': vendor_inv_bucket.id, 'vendor_id': final_vendor_id.id})

    @api.depends('bill_bucket_id')
    def _compute_bill_bucket_amount(self):
        self.bill_bucket_amount = 0.0
        if self.bill_bucket_id:
            self.bill_bucket_amount = self.bill_bucket_id.bucket_amount


    def button_draft(self):
        res = super(AccountMove, self).button_draft()
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
                                    existing_rec = self.env['vendor.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', self.id),
                                         ('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id)])
                                    if existing_rec:
                                        existing_rec.unlink()

                                    if vendor_line.total_amount_invoiced == buget_inv_line.amount:
                                        print("iff")
                                        vendor_line.total_amount_invoiced = 0.0
                                    else:
                                        print("else")
                                        vendor_line.total_amount_invoiced -= buget_inv_line.amount
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
                                    existing_rec = self.env['user.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', self.id),
                                         ('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                         ('user_id', '=', buget_inv_line.budget_user_id.id)])
                                    if existing_rec:
                                        for del_rec in existing_rec:
                                            del_rec.unlink()
                                    cr = self.env.cr
                                    cr.execute(
                                        "SELECT id FROM invoice_budget_line where check_invoice_posted = '%s' and budget_user_id = '%s' and bucket_type_id = '%s' and prod_inv_id != '%s'",
                                        (True, buget_inv_line.budget_user_id.id, buget_inv_line.bucket_type_id.id,
                                         self.id))
                                    survey_user_ids = cr.fetchall()
                                    if not survey_user_ids:
                                        user_line.unlink()
                                    buget_inv_line.check_invoice_posted = False

            if self.product_remaining_budget_line:
                for budget_remaining_line in self.product_remaining_budget_line:
                    if not budget_remaining_line.released and budget_remaining_line.check_invoice_posted:

                        # --------------------------------------
                        # budget_remaining_line invoiced checkbox true
                        # ----------------------------------------
                        remaining_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                             ('bucket_status', '=', 'invoiced')])
                        remaining_bucket.bucket_amount -= budget_remaining_line.amount
                        if remaining_bucket.vendor_line:
                            for vendor_line in remaining_bucket.vendor_line:
                                if vendor_line.vendor_id.id == budget_remaining_line.budget_inv_remaining_vendor_id.id:
                                    existing_rec = self.env['vendor.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', self.id),
                                         ('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id)])
                                    if existing_rec:
                                        existing_rec.unlink()
                                    if vendor_line.total_amount_invoiced == budget_remaining_line.amount:
                                        print("iff")
                                        vendor_line.total_amount_invoiced = 0.0
                                    else:
                                        print("else")
                                        vendor_line.total_amount_invoiced -= budget_remaining_line.amount
    
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
                                    existing_rec = self.env['user.invoice.detail'].sudo().search(
                                        [('invoice_name', '=', self.id),
                                         ('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                         ('user_id', '=', budget_remaining_line.budget_remaining_user_id.id)])
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

        if self.move_type == 'in_invoice':
            if self.invoice_line_ids:
                for vendor_bill_line in self.invoice_line_ids:
                    fixed_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', vendor_bill_line.bucket_ids.bucket_type_id.id),
                         ('bucket_status', '=', 'billed')])
                    fixed_bucket.bucket_amount -= vendor_bill_line.price_subtotal
                    if fixed_bucket.vendor_line:
                        for vendor_line in fixed_bucket.vendor_line:
                            if vendor_line.vendor_id.id == self.partner_id.id:
                                existing_rec = self.env['vendor.bill.detail'].sudo().search(
                                    [('bill_name', '=', self.id),
                                     ('bucket_type_id', '=', vendor_bill_line.bucket_ids.bucket_type_id.id),
                                     ('vendor_id', '=', self.partner_id.id)])
                                if existing_rec:
                                    existing_rec.unlink()

                            vendor_line.total_amount_invoiced -= vendor_bill_line.price_subtotal

        return res

    @api.model_create_multi
    def create(self, vals_list):
        rec = super(AccountMove, self).create(vals_list)
        if rec.move_type == 'out_invoice':
            if rec.invoice_line_ids:
                for inv_line in rec.invoice_line_ids:
                    if inv_line.product_id and inv_line.product_id.product_tmpl_id and inv_line.product_id.product_fixed_budget_line:
                        for fix_budget_line in inv_line.product_id.product_fixed_budget_line:
                            budget_data = self.env['invoice.budget.line'].sudo().create({
                                'product_id_budget': fix_budget_line.product_id.id,
                                'name': fix_budget_line.name,
                                'prod_inv_id': rec.id,
                                'account_move_line_id': inv_line.id,
                                'bucket_type_id': fix_budget_line.bucket_type_id.id,
                                'assignable_status': fix_budget_line.assignable_status,
                                'amount': fix_budget_line.amount * inv_line.quantity,
                                'is_vendor': fix_budget_line,
                                'budget_inv_vendor_id': fix_budget_line.prod_fix_vendor_id.id,
                                'budget_user_id': fix_budget_line.prod_fix_assigned_user_id.id,
                                'prod_priority': fix_budget_line.prod_priority
                            })

                    if inv_line.product_id and inv_line.product_id.product_tmpl_id and inv_line.product_id.product_allocate_budget_line:
                        for allocate_budget_line in inv_line.product_id.product_allocate_budget_line:
                            remaining_budget_data = self.env['product.budget.remaining'].sudo().create({
                                'product_id_budget': allocate_budget_line.product_id.id,
                                'name': allocate_budget_line.name,
                                'prod_remaining_id': rec.id,
                                'account_move_line_id': inv_line.id,
                                'bucket_type_id': allocate_budget_line.bucket_type_id.id,
                                'assignable_status': allocate_budget_line.assignable_status,
                                'is_vendor': allocate_budget_line,
                                'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
                                'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
                                'allocate_percent': allocate_budget_line.allocate_percent,
                                'amount': allocate_budget_line.amount * inv_line.quantity
                            })

        return rec



    def write(self, vals):
        old_inv_line_ids= self.inv_budget_line
        if self.move_type == 'out_invoice':
            if vals.get('invoice_line_ids'):
                for old_fixed in self.inv_budget_line:
                    old_fixed.unlink()
                for old_remaining in self.product_remaining_budget_line:
                    old_remaining.unlink()

        res = super(AccountMove, self).write(vals)
        if self.move_type == 'out_invoice':
            if vals.get('invoice_line_ids'):
                for new_inv in self.invoice_line_ids:
                    if new_inv.product_id and new_inv.product_id.product_tmpl_id and new_inv.product_id.product_tmpl_id.product_fixed_budget_line:
                        for fix_budget_line in new_inv.product_id.product_tmpl_id.product_fixed_budget_line:
                                budget_data = self.env['invoice.budget.line'].sudo().create({
                                    'product_id_budget': fix_budget_line.product_id.id,
                                    'name': fix_budget_line.name,
                                    'prod_inv_id': self.id,
                                    'account_move_line_id': new_inv.id,
                                    'bucket_type_id': fix_budget_line.bucket_type_id.id,
                                    'assignable_status': fix_budget_line.assignable_status,
                                    # 'amount': fix_budget_line.amount,
                                    'amount': fix_budget_line.amount * new_inv.quantity,
                                    'is_vendor': fix_budget_line,
                                    'budget_inv_vendor_id': fix_budget_line.prod_fix_vendor_id.id,
                                    'budget_user_id': fix_budget_line.prod_fix_assigned_user_id.id,
                                    'prod_priority': fix_budget_line.prod_priority
                                })

                    if new_inv.product_id and new_inv.product_id.product_tmpl_id and new_inv.product_id.product_tmpl_id.product_allocate_budget_line:
                            for allocate_budget_line in new_inv.product_id.product_tmpl_id.product_allocate_budget_line:
                                remaining_budget_data = self.env['product.budget.remaining'].sudo().create({
                                    'product_id_budget': allocate_budget_line.product_id.id,
                                    'name': allocate_budget_line.name,
                                    'prod_remaining_id': self.id,
                                    'account_move_line_id': new_inv.id,
                                    'bucket_type_id': allocate_budget_line.bucket_type_id.id,
                                    'assignable_status': allocate_budget_line.assignable_status,
                                    'is_vendor': allocate_budget_line,
                                    'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
                                    'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
                                    'allocate_percent': allocate_budget_line.allocate_percent,
                                    # 'amount': allocate_budget_line.amount
                                    'amount': allocate_budget_line.amount * new_inv.quantity
                                })
        return res

    # def write(self, vals):
    #     if self.move_type == 'out_invoice':
    #         if vals.get('invoice_line_ids'):
    #             for ss in self.inv_budget_line:
    #                 ss.unlink()
    #     res = super(AccountMove, self).write(vals)
    #     if self.move_type == 'out_invoice':
    #         if vals.get('invoice_line_ids'):
    #             for addedline, addedlineid in zip(vals.get('invoice_line_ids'), self.invoice_line_ids):
    #                 if addedline[1] != addedlineid.id:
    #                     if addedline[2] and addedline[2].get('product_id'):
    #                         product_id = self.env['product.product'].sudo().search(
    #                             [('id', '=', addedline[2]['product_id'])])
    #                         if addedline[2].get('quantity'):
    #                             quantity = addedline[2].get('quantity')
    #                         else:
    #                             quantity = 1
    #                         if product_id and product_id.product_tmpl_id and product_id.product_fixed_budget_line:
    #                             for fix_budget_line in product_id.product_fixed_budget_line:
    #                                 budget_data = self.env['invoice.budget.line'].sudo().create({
    #                                     'product_id_budget': fix_budget_line.product_id.id,
    #                                     'name': fix_budget_line.name,
    #                                     'prod_inv_id': self.id,
    #                                     'account_move_line_id': addedlineid.id,
    #                                     'bucket_type_id': fix_budget_line.bucket_type_id.id,
    #                                     'assignable_status': fix_budget_line.assignable_status,
    #                                     'amount': fix_budget_line.amount * quantity,
    #                                     'is_vendor': fix_budget_line,
    #                                     'budget_inv_vendor_id': fix_budget_line.prod_fix_vendor_id.id,
    #                                     'budget_user_id': fix_budget_line.prod_fix_assigned_user_id.id,
    #                                     'prod_priority': fix_budget_line.prod_priority
    #                                 })
    #
    #                         if product_id and product_id.product_tmpl_id and product_id.product_allocate_budget_line:
    #                             for allocate_budget_line in product_id.product_allocate_budget_line:
    #                                 remaining_budget_data = self.env['product.budget.remaining'].sudo().create({
    #                                     'product_id_budget': allocate_budget_line.product_id.id,
    #                                     'name': allocate_budget_line.name,
    #                                     'prod_remaining_id': self.id,
    #                                     'account_move_line_id': addedlineid.id,
    #                                     'bucket_type_id': allocate_budget_line.bucket_type_id.id,
    #                                     'assignable_status': allocate_budget_line.assignable_status,
    #                                     'is_vendor': allocate_budget_line,
    #                                     'budget_inv_remaining_vendor_id': allocate_budget_line.prod_remaining_budget_vendor_id.id,
    #                                     'budget_remaining_user_id': allocate_budget_line.prod_remaining_budget_assigned_user_id.id,
    #                                     'allocate_percent': allocate_budget_line.allocate_percent,
    #                                     'amount': allocate_budget_line.amount * quantity
    #                                 })
    #                 else:
    #                     if addedline[1] and addedline[2]:
    #                         if addedline[2].get('quantity'):
    #                             quantity = addedline[2].get('quantity')
    #                         else:
    #                             quantity = 1
    #                         move_line = self.env['account.move.line'].sudo().search([('id', '=', addedline[1])])
    #                         get_move_line_product = self.env['product.product'].sudo().search(
    #                             [('id', '=', move_line.product_id.id)])
    #                         inv_buget_line_product_link_recrd = self.env['invoice.budget.line'].sudo().search(
    #                             [('account_move_line_id', '=', addedline[1])])
    #                         remaining_budget_line_product_link_recrd = self.env[
    #                             'product.budget.remaining'].sudo().search([('account_move_line_id', '=', addedline[1])])
    #
    #                         if inv_buget_line_product_link_recrd:
    #                             for records in inv_buget_line_product_link_recrd:
    #                                 for fix_budget_line in get_move_line_product.product_fixed_budget_line:
    #                                     if fix_budget_line.prod_priority == records.prod_priority:
    #                                         records.amount = fix_budget_line.amount * quantity
    #                         if remaining_budget_line_product_link_recrd:
    #                             for recrd in remaining_budget_line_product_link_recrd:
    #                                 for allocate_budget_line in get_move_line_product.product_allocate_budget_line:
    #                                     if allocate_budget_line.allocate_percent == recrd.allocate_percent and allocate_budget_line.bucket_type_id.id == recrd.bucket_type_id.id:
    #                                         recrd.amount = allocate_budget_line.amount * quantity
    #
    #     return res

    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.move_type == 'out_invoice':
            priority_list = []
            bucket_type_list = set()
            assigned_vendor_lst = []
            assigned_user_lst = []
            if self.inv_budget_line:
                for inv_budget in self.inv_budget_line:
                    if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget != True and not inv_budget.budget_inv_vendor_id:
                        raise UserError(_("Please assign vendors in budgeting tab"))
                    if inv_budget.assignable_status == 'assignable_at_inv' and inv_budget == True and not inv_budget.budget_user_id:
                        raise UserError(_("Please assign Users in budgeting tab"))

                for inv_fix_budget in self.inv_budget_line:
                    priority_list.append(inv_fix_budget.prod_priority)
                    bucket_type_list.add(inv_fix_budget.bucket_type_id)
                remove_repitetion_priority_list = set(priority_list)
                final_priority_list = sorted(remove_repitetion_priority_list)

                for priority in final_priority_list:
                    for buget_inv_line in self.inv_budget_line:
                        if priority == buget_inv_line.prod_priority:
                            fixed_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'invoiced')])
                            fixed_bucket.bucket_amount += buget_inv_line.amount

                            buget_inv_line.check_invoice_posted = True

                            fixed_bucket_vendor_lst = []
                            fixed_bucket_user_lst = []

                            if fixed_bucket.vendor_line:
                                for fixed_vendr in fixed_bucket.vendor_line:
                                    fixed_bucket_vendor_lst.append(fixed_vendr.vendor_id.id)

                            if fixed_bucket.user_line:
                                for fixed_user in fixed_bucket.user_line:
                                    fixed_bucket_user_lst.append(fixed_user.user_id.id)

                            if buget_inv_line.budget_inv_vendor_id:
                                for vendr_id in buget_inv_line:
                                    if vendr_id.budget_inv_vendor_id.id not in fixed_bucket_vendor_lst:
                                        assigned_vendor_lst.append(vendr_id)
                            if buget_inv_line.budget_user_id:
                                for user_id in buget_inv_line.budget_user_id:
                                    if user_id.id not in fixed_bucket_user_lst:
                                        user_inv_bucket = self.env['bucket'].sudo().search(
                                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                             ('bucket_status', '=', 'invoiced')])
                                        existing_rec = self.env['user.line'].sudo().search(
                                            [('user_line_bucket_id', '=', user_inv_bucket.id),
                                             ('user_id', '=', user_id.id)])
                                        if not existing_rec:
                                            user_bucket_line = self.env['user.line'].sudo().create(
                                                {'user_line_bucket_id': user_inv_bucket.id,
                                                 'user_id': user_id.id})

            if self.product_remaining_budget_line:
                for rem_budget in self.product_remaining_budget_line:
                    if rem_budget.assignable_status == 'assignable_at_inv' and rem_budget != True and not rem_budget.budget_inv_remaining_vendor_id:
                        raise UserError(_("Please assign vendors in budgeting tab"))
                    if rem_budget.assignable_status == 'assignable_at_inv' and rem_budget == True and not rem_budget.budget_remaining_user_id:
                        raise UserError(_("Please assign Users in budgeting tab"))

                for budget_remaining_line in self.product_remaining_budget_line:
                    bucket_type_list.add(budget_remaining_line.bucket_type_id)
                    remaining_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                         ('bucket_status', '=', 'invoiced')])
                    remaining_bucket.bucket_amount += budget_remaining_line.amount

                    budget_remaining_line.check_invoice_posted = True
                    remaining_bucket_vendor_lst = []
                    remaining_bucket_user_lst = []
                    if remaining_bucket.vendor_line:
                        for remaining_vendr in remaining_bucket.vendor_line:
                            remaining_bucket_vendor_lst.append(remaining_vendr.id)

                    if remaining_bucket.user_line:
                        for remaining_user in remaining_bucket.user_line:
                            remaining_bucket_user_lst.append(remaining_user.id)

                    if budget_remaining_line.budget_inv_remaining_vendor_id:
                        for rem_vendr_id in budget_remaining_line:
                            if rem_vendr_id.id not in remaining_bucket_vendor_lst:
                                assigned_vendor_lst.append(rem_vendr_id)

                    if budget_remaining_line.budget_remaining_user_id:
                        for rem_user_id in budget_remaining_line.budget_remaining_user_id:
                            if rem_user_id.id not in remaining_bucket_user_lst:
                                user_inv_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'invoiced')])
                                existing_rec = self.env['user.line'].sudo().search(
                                    [('user_line_bucket_id', '=', user_inv_bucket.id),
                                     ('user_id', '=', rem_user_id.id)])
                                if not existing_rec:
                                    user_bucket_line = self.env['user.line'].sudo().create(
                                        {'user_line_bucket_id': user_inv_bucket.id,
                                         'user_id': rem_user_id.id})

                for bucket_type_id in bucket_type_list:
                    existing_bucket_dashboard = self.env['bucket.dashboard'].sudo().search(
                        [('bucket_type_id', '=', bucket_type_id.id)])
                    if not existing_bucket_dashboard:
                        self.env['bucket.dashboard'].sudo().create({
                            'bucket_type_id': bucket_type_id.id,
                            'bucket_inv_ids': [(4, self.id, 0)]
                        })
                    else:
                        existing_bucket_dashboard.bucket_inv_ids = [(4, self.id, 0)]

            assigned_vendr_set = set(assigned_vendor_lst)
            final_vendor_lst = list(assigned_vendr_set)

            assigned_user_set = set(assigned_user_lst)
            final_user_lst = list(assigned_user_set)

            vendor_bucket_type_id = self.env['bucket.type'].sudo().search([], limit=1)
            vendor_inv_bucket = self.env['bucket'].sudo().search(
                [('bucket_type_id', '=', vendor_bucket_type_id.id), ('bucket_status', '=', 'invoiced')])
            for final_vendor in final_vendor_lst:
                if final_vendor._name == 'product.budget.remaining':
                    final_vendor_id = self.env['res.partner'].browse(final_vendor.budget_inv_remaining_vendor_id.id)
                    vendor_inv_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', final_vendor.bucket_type_id.id),
                         ('bucket_status', '=', 'invoiced')])
                    existing_vendor = self.env['vendor.line'].sudo().search([("vendor_id", '=', final_vendor_id.id),
                                                                             ('vendor_line_bucket_id', '=',
                                                                              vendor_inv_bucket.id)])
                    if not existing_vendor:
                        vendor_bucket_line = self.env['vendor.line'].sudo().create(
                            {'vendor_line_bucket_id': vendor_inv_bucket.id, 'vendor_id': final_vendor_id.id})
                else:
                    final_vendor_id = self.env['res.partner'].browse(final_vendor.budget_inv_vendor_id.id)
                    vendor_inv_bucket_inv = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', final_vendor.bucket_type_id.id),
                         ('bucket_status', '=', 'invoiced')])
                    existing_vendor = self.env['vendor.line'].sudo().search([("vendor_id", '=', final_vendor_id.id),
                                                                             ('vendor_line_bucket_id', '=',
                                                                              vendor_inv_bucket_inv.id)])
                    if not existing_vendor:
                        vendor_bucket_line = self.env['vendor.line'].sudo().create(
                            {'vendor_line_bucket_id': vendor_inv_bucket_inv.id, 'vendor_id': final_vendor_id.id})
                # final_vendor_id = self.env['res.partner'].browse(final_vendor)
                # existing_vendor = self.env['vendor.line'].sudo().search([("vendor_id", '=', final_vendor_id.id),('vendor_line_bucket_id', '=', budget_remaining_line.bucket_type_id.id)])
                # if not existing_vendor:
                #     vendor_bucket_line = self.env['vendor.line'].sudo().create(
                #         {'vendor_line_bucket_id': vendor_inv_bucket.id, 'vendor_id': final_vendor_id.id})
        if self.move_type == 'in_invoice':
            if self.partner_id:
                if self.invoice_line_ids:
                    for move_lines in self.invoice_line_ids:
                        billed_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', move_lines.bucket_ids.bucket_type_id.id),
                             ('bucket_status', '=', 'billed')])
                        billed_bucket.bucket_amount += move_lines.price_subtotal
                        if move_lines.bucket_ids.bucket_type_id:
                            existing_vendor = self.env['vendor.line.released'].sudo().search(
                                [("vendor_id", '=', self.partner_id.id),('vendor_line_released_bucket_id','=',move_lines.bucket_ids.id)])

                            if not existing_vendor:
                                vendor_bucket_line = self.env['vendor.line.released'].sudo().create(
                                    {'vendor_line_released_bucket_id': move_lines.bucket_ids.id, 'vendor_id': self.partner_id.id})

                        if move_lines.bucket_ids.bucket_type_id:
                            vendor_bill_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', move_lines.bucket_ids.bucket_type_id.id),
                                 ('bucket_status', '=', 'billed')])
                            existing_vendor = self.env['vendor.line'].sudo().search(
                                [("vendor_id", '=', self.partner_id.id),
                                 ('vendor_line_bucket_id', '=', vendor_bill_bucket.id)])

                            if not existing_vendor:
                                vendor_bucket_line = self.env['vendor.line'].sudo().create(
                                    {'vendor_line_bucket_id': vendor_bill_bucket.id,
                                     'vendor_id': self.partner_id.id})

        return res


class InvoiceBudgetLine(models.Model):
    _name = "invoice.budget.line"

    name = fields.Text(string='Description', readonly=False)
    product_id_budget = fields.Many2one('product.template', 'Product')
    prod_inv_id = fields.Many2one('account.move', 'Prod Invoice Id')
    account_move_line_id = fields.Many2one('account.move.line', 'Prod Move Line')
    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    budget_inv_vendor_id = fields.Many2one('res.partner', string="Name", copy=False)
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
    account_move_line_id = fields.Many2one('account.move.line', 'Prod Allocate Move Line')

    assignable_status = fields.Selection([('assigned', 'Assigned'),
                                          ('unassigned', 'Unassigned'),
                                          ('assignable_at_inv', 'Assignable At Time of Invoice')
                                          ], "Assignable Status")
    is_vendor = fields.Boolean(string='Is Vendor')
    budget_inv_remaining_vendor_id = fields.Many2one('res.partner', string="Name", copy=False)
    budget_remaining_user_id = fields.Many2one('res.partner', string="Name", copy=False)

    bucket_type_id = fields.Many2one('bucket.type', 'Bucket Type')
    amount = fields.Float("Amount")
    invoiced = fields.Boolean('Invoiced')
    released = fields.Boolean('Released')
    amount_residual = fields.Float('Amount Due')
    check_invoice_posted = fields.Boolean('check invoice posted')
    item_refunded = fields.Boolean('Refunded')
    refund_residual = fields.Float('Refund Due')


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'


    def create_payment_in_invoice_partial(self,invoice_amount,total_released_amount):
        if invoice_amount.invoice_line_ids:
            for bill_line in invoice_amount.invoice_line_ids:
                if not bill_line.is_partial and not bill_line.is_bill_paid:
                    if total_released_amount > bill_line.price_subtotal:
                        bill_line.bucket_ids.bucket_amount -= bill_line.price_subtotal
                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.bill_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.is_partial = True

                                else:
                                    bill_line.bill_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.bill_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.bill_residual_amount = 0.0
                                else:
                                    bill_line.bill_residual_amount = bill_line.bill_residual_amount - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_paid:
                            bill_line.bill_residual_amount = bill_line.price_subtotal
                        total_released_amount -= bill_line.price_subtotal
                    else:
                        bill_line.bucket_ids.bucket_amount -= total_released_amount
                        billed_bucket_type = self.env['bucket.type'].search(
                            [('id', '=', bill_line.bucket_ids.bucket_type_id.id)])
                        if billed_bucket_type:
                            bill_bucket = self.env['bucket'].search(
                                [('bucket_type_id', '=', billed_bucket_type.id), ('bucket_status', '=', 'billed')])
                            bill_bucket.bucket_amount -= total_released_amount
                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.bill_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.is_partial = True

                                else:
                                    bill_line.bill_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.bill_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.bill_residual_amount = 0.0
                                else:
                                    bill_line.bill_residual_amount = bill_line.bill_residual_amount - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_paid:
                            bill_line.bill_residual_amount = bill_line.price_subtotal
                elif bill_line.is_partial and not bill_line.is_bill_paid:
                    if bill_line.bill_residual_amount >= total_released_amount:
                        bill_line.bucket_ids.bucket_amount -= total_released_amount
                        billed_bucket_type = self.env['bucket.type'].search(
                            [('id', '=', bill_line.bucket_ids.bucket_type_id.id)])
                        if billed_bucket_type:
                            bill_bucket = self.env['bucket'].search(
                                [('bucket_type_id', '=', billed_bucket_type.id), ('bucket_status', '=', 'billed')])
                            bill_bucket.bucket_amount -= total_released_amount
                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.bill_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.is_partial = True

                                else:
                                    bill_line.bill_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.bill_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.bill_residual_amount = 0.0
                                else:
                                    bill_line.bill_residual_amount = bill_line.bill_residual_amount - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_paid:
                            bill_line.bill_residual_amount = bill_line.price_subtotal

                    else:
                        bill_line.bucket_ids.bucket_amount -= bill_line.bill_residual_amount
                        billed_bucket_type = self.env['bucket.type'].search(
                            [('id', '=', bill_line.bucket_ids.bucket_type_id.id)])
                        if billed_bucket_type:
                            bill_bucket = self.env['bucket'].search(
                                [('bucket_type_id', '=', billed_bucket_type.id), ('bucket_status', '=', 'billed')])
                            bill_bucket.bucket_amount -= bill_line.bill_residual_amount
                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.bill_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.is_partial = True

                                else:
                                    bill_line.bill_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.bill_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.bill_residual_amount
                                    bill_line.is_bill_paid = True
                                    bill_line.bill_residual_amount = 0.0
                                else:
                                    bill_line.bill_residual_amount = bill_line.bill_residual_amount - total_released_amount
                                    bill_line.is_partial = True

                                    if bill_line.bill_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_paid:
                            bill_line.bill_residual_amount = bill_line.price_subtotal

                        total_released_amount = total_released_amount - bill_line.bill_residual_amount

    def create_payment_in_invoice_paid(self, invoice_amount):
        if invoice_amount.invoice_line_ids:
            for bill_line in invoice_amount.invoice_line_ids:
                if not bill_line.bill_residual_amount:
                    if not bill_line.is_bill_paid:
                        if bill_line.bill_residual_amount != 0.0:
                            bill_line.bucket_ids.bucket_amount -= bill_line.bill_residual_amount
                            billed_bucket_type = self.env['bucket.type'].search([('id','=',bill_line.bucket_ids.bucket_type_id.id)])
                            if billed_bucket_type:
                                bill_bucket = self.env['bucket'].search([('bucket_type_id','=',billed_bucket_type.id),('bucket_status','=','billed')])
                                bill_bucket.bucket_amount -= bill_line.bill_residual_amount
                        else:
                            billed_bucket_type = self.env['bucket.type'].search(
                                [('id', '=', bill_line.bucket_ids.bucket_type_id.id)])
                            bill_line.bucket_ids.bucket_amount -= bill_line.price_subtotal
                            if billed_bucket_type:
                                bill_bucket = self.env['bucket'].search([('bucket_type_id','=',billed_bucket_type.id),('bucket_status','=','billed')])
                                bill_bucket.bucket_amount -= bill_line.price_subtotal
                        if bill_line.bucket_ids.bucket_type_id:
                            if not bill_line.is_bill_paid:
                                bill_line.is_bill_paid = True
                                bill_line.is_partial = True

                                bill_line.bill_residual_amount = 0.0

                        else:
                            if not bill_line.is_bill_paid:
                                bill_line.is_bill_paid = True
                                bill_line.is_partial = True

                                bill_line.bill_residual_amount = 0.0
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})
                    bill_line.update({"bill_residual_amount": 0.0})

                else:
                    if not bill_line.is_bill_paid:
                        if bill_line.bill_residual_amount != 0.0:
                            bill_line.bucket_ids.bucket_amount -= bill_line.bill_residual_amount
                            billed_bucket_type = self.env['bucket.type'].search(
                                [('id', '=', bill_line.bucket_ids.bucket_type_id.id)])
                            if billed_bucket_type:
                                bill_bucket = self.env['bucket'].search(
                                    [('bucket_type_id', '=', billed_bucket_type.id), ('bucket_status', '=', 'billed')])
                                bill_bucket.bucket_amount -= bill_line.bill_residual_amount

                        else:
                            bill_line.bucket_ids.bucket_amount -= bill_line.price_unit
                            billed_bucket_type = self.env['bucket.type'].search(
                                [('id', '=', bill_line.bucket_ids.bucket_type_id.id)])
                            if billed_bucket_type:
                                bill_bucket = self.env['bucket'].search(
                                    [('bucket_type_id', '=', billed_bucket_type.id), ('bucket_status', '=', 'billed')])
                                bill_bucket.bucket_amount -= bill_line.price_unit
                        if bill_line.bucket_ids.bucket_type_id:
                            if not bill_line.is_bill_paid:
                                bill_line.is_bill_paid = True
                                bill_line.bill_residual_amount = 0.0

                        else:
                            if not bill_line.is_bill_paid:
                                bill_line.is_bill_paid = True
                                bill_line.bill_residual_amount = 0.0
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})
                    bill_line.update({"bill_residual_amount": 0.0})


    def create_payment_out_invoice_partial(self, total_released_amount):
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
                                        [('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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
                                total_released_amount = buget_inv_line.amount - total_released_amount

                                vendor_released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                if buget_inv_line.budget_inv_vendor_id:
                                    existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                        [('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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

                                if buget_inv_line.amount_residual != 0.0:
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
                                        [('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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
                                        [('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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
        if self.line_ids.move_id.product_remaining_budget_line and len(
                self.line_ids.move_id.inv_budget_line) == len(line_amount_released):
            for budget_remaining_line in self.line_ids.move_id.product_remaining_budget_line:

                if total_released_amount != 0 and not budget_remaining_line.released:
                    if budget_remaining_line.amount_residual == 0.0:
                        if total_released_amount >= budget_remaining_line.amount:
                            total_released_amount = total_released_amount - budget_remaining_line.amount
                            budget_remaining_line.released = True
                            invoiced_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'invoiced')])
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
                                    [('vendor_id', '=',
                                      budget_remaining_line.budget_inv_remaining_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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
                                    [('vendor_id', '=',
                                      budget_remaining_line.budget_inv_remaining_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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
                            budget_remaining_line.released = True

                            ############################################################3

                            vendor_released_bucket = self.env['bucket'].sudo().search(
                                [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                 ('bucket_status', '=', 'released')])

                            if budget_remaining_line.budget_inv_remaining_vendor_id:

                                existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                    [('vendor_id', '=',
                                      budget_remaining_line.budget_inv_remaining_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
                                
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
                                    [('vendor_id', '=',
                                      budget_remaining_line.budget_inv_remaining_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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

    def create_payment_out_invoice_in_payment(self):
        if self.line_ids.move_id.inv_budget_line:
            priority_list = []
            for inv_fix_budget in self.line_ids.move_id.inv_budget_line:
                priority_list.append(inv_fix_budget.prod_priority)
            priority_list.sort()
            for priority in priority_list:
                for buget_inv_line in self.line_ids.move_id.inv_budget_line:
                    if priority == buget_inv_line.prod_priority and not buget_inv_line.released:
                        invoices_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                             ('bucket_status', '=', 'invoiced')])
                        invoices_bucket.bucket_amount = invoices_bucket.bucket_amount - buget_inv_line.amount
                        released_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        released_bucket.bucket_amount = released_bucket.bucket_amount + buget_inv_line.amount
                        buget_inv_line.released = True
                        # ////////////////////////////////
                        vendor_released_bucket = self.env['bucket'].sudo().search(
                            [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                             ('bucket_status', '=', 'released')])
                        if buget_inv_line.budget_inv_vendor_id:
                            existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                                [('vendor_id', '=', buget_inv_line.budget_inv_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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

        if self.line_ids.move_id.product_remaining_budget_line:

            for budget_remaining_line in self.line_ids.move_id.product_remaining_budget_line:
                if not budget_remaining_line.released:
                    invoiced_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                         ('bucket_status', '=', 'invoiced')])
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
                            [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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

    def create_payment_out_invoice_paid(self,invoice_amount):
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
                            [('vendor_id', '=', inv_budget_line.budget_inv_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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
            for budget_remaining_line in self.line_ids.move_id.product_remaining_budget_line:
                if not budget_remaining_line.released:
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

                    vendor_released_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                         ('bucket_status', '=', 'released')])
                    if budget_remaining_line.budget_inv_remaining_vendor_id:
                        existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                            [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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
                if not budget_remaining_line.released and budget_remaining_line.amount_residual != 0.0:

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

                    vendor_released_bucket = self.env['bucket'].sudo().search(
                        [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                         ('bucket_status', '=', 'released')])
                    if budget_remaining_line.budget_inv_remaining_vendor_id:
                        existing_vendor_rel_line = self.env['vendor.line.released'].sudo().search(
                            [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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

                elif not budget_remaining_line.released and budget_remaining_line.amount_residual == 0.0:
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
                            [('vendor_id', '=', budget_remaining_line.budget_inv_remaining_vendor_id.id),('vendor_line_released_bucket_id','=',vendor_released_bucket.id)])
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

    def create_payment_out_refund_partial(self,total_released_amount):
        if self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
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

        allocate_line_amount_released = []
        for budget_remaining_line in self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
            if budget_remaining_line.item_refunded:
                allocate_line_amount_released.append(budget_remaining_line.item_refunded)
        if self.line_ids.move_id.reversed_entry_id.inv_budget_line and len(
                self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line) == len(
            allocate_line_amount_released):
            priority_list = []
            for inv_fix_budget in self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                priority_list.append(inv_fix_budget.prod_priority)
            final_priority_list = sorted(set(priority_list), reverse=True)
            for priority in final_priority_list:
                for buget_inv_line in self.line_ids.move_id.reversed_entry_id.inv_budget_line:
                    if priority == buget_inv_line.prod_priority and total_released_amount != 0.0 and not buget_inv_line.item_refunded:
                        if buget_inv_line.refund_residual == 0.0:
                            if total_released_amount >= buget_inv_line.amount:
                                total_released_amount = total_released_amount - buget_inv_line.amount
                                buget_inv_line.item_refunded = True

                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount -= buget_inv_line.amount

                            else:
                                buget_inv_line.refund_residual = buget_inv_line.amount - total_released_amount

                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', buget_inv_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount -= total_released_amount
                                total_released_amount = buget_inv_line.amount - total_released_amount

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

    def create_payment_out_refund_paid(self):
        if self.line_ids.move_id.reversed_entry_id.invoice_line_ids:
            for move_line_id in self.line_ids.move_id.reversed_entry_id.invoice_line_ids:
                if self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:

                    for budget_remaining_line in self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
                        if budget_remaining_line.released and move_line_id.id == budget_remaining_line.account_move_line_id.id and not budget_remaining_line.item_refunded:
                            if budget_remaining_line.refund_residual == 0.0:
                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])
                                released_bucket.bucket_amount -= budget_remaining_line.amount

                                budget_remaining_line.item_refunded = True
                                budget_remaining_line.refund_residual = 0.0
                            else:
                                released_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', budget_remaining_line.bucket_type_id.id),
                                     ('bucket_status', '=', 'released')])

                                released_bucket.bucket_amount -= budget_remaining_line.refund_residual

                                budget_remaining_line.item_refunded = True
                                budget_remaining_line.refund_residual = 0.0
                allocate_line_amount_released = []
                for budget_remaining_line in self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line:
                    if budget_remaining_line.item_refunded:
                        allocate_line_amount_released.append(budget_remaining_line.item_refunded)
                if len(self.line_ids.move_id.reversed_entry_id.product_remaining_budget_line) == len(
                        allocate_line_amount_released):
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
                                    buget_inv_line.refund_residual = 0.0


    def create_payment_in_refund_partial(self,invoice_amount,total_released_amount):
        if invoice_amount.reversed_entry_id.invoice_line_ids:
            for bill_line in invoice_amount.reversed_entry_id.invoice_line_ids:
                if not bill_line.is_refund_partial and not bill_line.is_bill_refunded:
                    if total_released_amount > bill_line.price_subtotal:
                        bill_line.bucket_ids.bucket_amount += bill_line.price_subtotal

                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_paid:
                            if bill_line.refund_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.is_refund_partial = True

                                else:
                                    bill_line.refund_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.refund_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.refund_residual_amount = 0.0
                                else:
                                    bill_line.refund_residual_amount = bill_line.refund_residual_amount - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_refunded:
                            bill_line.refund_residual_amount = bill_line.price_subtotal
                        total_released_amount -= bill_line.price_subtotal
                    else:
                        bill_line.bucket_ids.bucket_amount += total_released_amount

                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_refunded:
                            if bill_line.refund_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.is_refund_partial = True

                                else:
                                    bill_line.refund_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.refund_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.refund_residual_amount = 0.0
                                else:
                                    bill_line.refund_residual_amount = bill_line.refund_residual_amount - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_refunded:
                            bill_line.refund_residual_amount = bill_line.price_subtotal
                elif bill_line.is_refund_partial and not bill_line.is_bill_refunded:
                    if bill_line.refund_residual_amount >= total_released_amount:
                        bill_line.bucket_ids.bucket_amount += total_released_amount
                        #billed amount update for bucket status billed

                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_refunded:
                            if bill_line.refund_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.is_refund_partial = True

                                else:
                                    bill_line.refund_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.refund_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.refund_residual_amount = 0.0
                                else:
                                    bill_line.refund_residual_amount = bill_line.refund_residual_amount - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_refunded:
                            bill_line.refund_residual_amount = bill_line.price_subtotal

                    else:
                        bill_line.bucket_ids.bucket_amount += bill_line.refund_residual_amount
                        if not bill_line.bucket_ids.bucket_type_id:
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                        if total_released_amount != 0.0 and not bill_line.is_bill_refunded:
                            if bill_line.refund_residual_amount == 0.0:
                                if total_released_amount >= bill_line.price_subtotal:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.is_refund_partial = True

                                else:
                                    bill_line.refund_residual_amount = bill_line.price_subtotal - total_released_amount
                                    total_released_amount = bill_line.price_subtotal - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                            else:
                                if total_released_amount >= bill_line.refund_residual_amount:
                                    total_released_amount = total_released_amount - bill_line.refund_residual_amount
                                    bill_line.is_bill_refunded = True
                                    bill_line.refund_residual_amount = 0.0
                                else:
                                    bill_line.refund_residual_amount = bill_line.refund_residual_amount - total_released_amount
                                    bill_line.is_refund_partial = True

                                    if bill_line.refund_residual_amount != 0.0:
                                        total_released_amount = 0
                        elif total_released_amount == 0 and not bill_line.is_bill_refunded:
                            bill_line.refund_residual_amount = bill_line.price_subtotal

                        total_released_amount = total_released_amount - bill_line.refund_residual_amount


    def create_payment_in_refund_paid(self,invoice_amount):
        if invoice_amount.reversed_entry_id.invoice_line_ids:
            for bill_line in invoice_amount.reversed_entry_id.invoice_line_ids:
                if bill_line.refund_residual_amount == 0.0:
                    if not bill_line.is_bill_refunded:
                        if bill_line.refund_residual_amount != 0.0:
                            bill_line.bucket_ids.bucket_amount += bill_line.refund_residual_amount
                        else:
                            bill_line.bucket_ids.bucket_amount += bill_line.price_subtotal
                        if bill_line.bucket_ids.bucket_type_id:
                            if not bill_line.is_bill_refunded:
                                bill_line.is_bill_refunded = True
                                bill_line.is_refund_partial = True

                                bill_line.refund_residual_amount = 0.0

                        else:
                            if not bill_line.is_bill_refunded:
                                bill_line.is_bill_refunded = True
                                bill_line.is_refund_partial = True

                                bill_line.refund_residual_amount = 0.0
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

                else:
                    if not bill_line.is_bill_refunded:
                        if bill_line.refund_residual_amount != 0.0:
                            bill_line.bucket_ids.bucket_amount += bill_line.refund_residual_amount
                        else:
                            bill_line.bucket_ids.bucket_amount += bill_line.price_unit
                        if bill_line.bucket_ids.bucket_type_id:
                            if not bill_line.is_bill_refunded:
                                bill_line.is_bill_refunded = True
                                bill_line.refund_residual_amount = 0.0

                        else:
                            if not bill_line.is_bill_refunded:
                                bill_line.is_bill_refunded = True
                                bill_line.refund_residual_amount = 0.0
                            vendor = self.env["vendor.line.released.inside.user"].sudo().search(
                                [('vendor_id', '=', self.line_ids.move_id.partner_id.id),
                                 ('vendor_line_released_bucket_id', "=", bill_line.bucket_ids.id)])
                            if not vendor:
                                vendor_line_released = self.env[
                                    "vendor.line.released.inside.user"].sudo().create(
                                    {"vendor_id": self.line_ids.move_id.partner_id.id,
                                     "vendor_line_released_bucket_id": bill_line.bucket_ids.id})

    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        invoice_amount = self.env['account.move'].sudo().search([('id', '=', self.line_ids.move_id.id)])
        #bill
        if invoice_amount.move_type == 'in_invoice':
            total_released_amount = self.amount
            if invoice_amount.amount_total > self.amount and invoice_amount.payment_state == "partial":
                self.create_payment_in_invoice_partial(invoice_amount,total_released_amount)

            else:
                self.create_payment_in_invoice_paid(invoice_amount)
        #invoice
        if invoice_amount.move_type == 'out_invoice':
            total_released_amount = self.amount
            self.line_ids.move_id.previous_released_amount += self.amount
            if invoice_amount.amount_total == self.amount and invoice_amount.payment_state in ("paid", "in_payment"):
                print("if outtt")
                self.create_payment_out_invoice_in_payment()

            elif invoice_amount.amount_total > self.amount and invoice_amount.payment_state == "partial":
                print("elif aout")
                self.create_payment_out_invoice_partial(total_released_amount)
            else:
                self.create_payment_out_invoice_paid(invoice_amount)
        #credit note invoice
        if invoice_amount.move_type == 'out_refund':
            total_released_amount = self.amount

            if invoice_amount.reversed_entry_id.move_type == "out_invoice":
                if invoice_amount.amount_total > self.amount and invoice_amount.payment_state == "partial":
                    self.create_payment_out_refund_partial(total_released_amount)

                else:
                    self.create_payment_out_refund_paid()
        #credit note bill
        if invoice_amount.move_type == "in_refund":
            total_released_amount = self.amount
            if invoice_amount.amount_total > self.amount and invoice_amount.payment_state == "partial":
                self.create_payment_in_refund_partial(invoice_amount, total_released_amount)
            else:
                self.create_payment_in_refund_paid(invoice_amount)

        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    inv_budget_line = fields.One2many('invoice.budget.line', 'account_move_line_id', 'Budget Info')
    remaining_budget_line = fields.One2many('product.budget.remaining', 'account_move_line_id', 'Budget Info')
    is_bill_paid = fields.Boolean('Paid')
    is_bill_refunded = fields.Boolean('Refund')
    is_partial = fields.Boolean('Partial')
    is_refund_partial = fields.Boolean('Refund Partial')
    bill_residual_amount = fields.Float('Due Amount')
    refund_residual_amount = fields.Float('Refund Due Amount')
    parent_move_type = fields.Selection(related='move_id.move_type', store=True, readonly=True, precompute=True, )
    bucket_ids = fields.Many2one('bucket', string="Buckets",copy=False)


    def popup_button(self):
        if self.bucket_ids:
            if self.bucket_ids.bucket_type_id:
                vendor_lines = self.env['vendor.line.released'].sudo().search([('vendor_line_released_bucket_id','=',self.bucket_ids.id)])
                for rec in vendor_lines:
                    rec.fetch_ven_bill_details()
            else:
                vendor_lines = self.env['vendor.line.released.inside.user'].sudo().search([('vendor_line_released_bucket_id','=',self.bucket_ids.id)])
                for rec in vendor_lines:
                    rec.fetch_ven_bills_details_inside_user()
            for rec in vendor_lines:
                record_vals = dict(
                    name = rec.vendor_id.id,
                    bucket_id = self.bucket_ids.id,
                    vendor_amount = rec.total_amount_released - rec.total_amount_billed
                )

                existing_vendor = self.env['show.vendors'].sudo().search([('name','=',rec.vendor_id.id),('bucket_id','=',self.bucket_ids.id)])
                if not existing_vendor:
                    self.env['show.vendors'].sudo().create(record_vals)
                else:
                    existing_vendor.update(record_vals)

        domain = [('bucket_id','=',self.bucket_ids.id)]


        vals = {
            'name': _('Show Vendor Bucket'),
            'type': 'ir.actions.act_window',
            'domain': domain,
            'view_type': 'form',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'show.vendors',
        }
        return vals

    @api.onchange('product_id')
    def _onchange_product_id(self):
        result = {}
        lst = []
        product_id = False

        if self.move_id.move_type in ('in_invoice'):
            product_id = self.env['product.supplierinfo'].sudo().search(
                [('partner_id', '=', self.move_id.partner_id.id)])

            if product_id:
                for products in product_id:
                    lst.append(products.product_tmpl_id.id)
            result['domain'] = {'product_id': [('product_tmpl_id', 'in', lst)]}
            return result


    def unlink(self):
        for rec in self:
            if rec.move_id.move_type == 'out_invoice':
                for record in rec.move_id.inv_budget_line:
                    if record and record.account_move_line_id.id == rec.id:
                        record.unlink()
                for record1 in rec.move_id.product_remaining_budget_line:
                    if record1 and record1.account_move_line_id.id == rec.id:
                        record1.unlink()
        res = super(AccountMoveLine, self).unlink()
        return res