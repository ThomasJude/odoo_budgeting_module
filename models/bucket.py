# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class Bucket(models.Model):
    _name = "bucket"

    name = fields.Char(string='Name')
    bucket_amount = fields.Float(string='Bucket Amount',)
    bucket_status = fields.Selection([('invoiced','Invoiced'),('released','Released'),('billed','Billed')], "Bucket Status")
    bucket_type_id = fields.Many2one('bucket.type','Bucket Type')
    vendor_line = fields.One2many('vendor.line', 'vendor_line_bucket_id', 'Vendor Details')
    user_line = fields.One2many('user.line', 'user_line_bucket_id', 'User Details')
    vendor_line_released = fields.One2many('vendor.line.released', 'vendor_line_released_bucket_id', 'Vendor Released Details')
    user_line_released = fields.One2many('user.line.released', 'user_line_released_bucket_id', 'User Released Details')

    vendor_line_released_inside_user = fields.One2many('vendor.line.released.inside.user',"vendor_line_released_bucket_id","Vendor Bill Details")

    check = fields.Boolean(compute='_get_value')
    check2 = fields.Boolean(compute='_get_status')
    # check3 = fields.Boolean(compute='_remove_vendor_line')



    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{} ({})".format(record.name, round(record.bucket_amount,2))))
        return result

    def unlink(self):
        if not self.env.user.has_group('odoo_budgeting_module.bucket_delete_group'):
            raise UserError("You don't have permission to delete this record.")
        return super(Bucket,self).unlink()


    @api.constrains('bucket_status','bucket_type_id')
    def bucket_user_type_status(self):
        total = 0
        for record in self:
            obj = self.env['bucket'].search([('bucket_status','=',record.bucket_status),('id','!=',record.id),('bucket_type_id','=',record.bucket_type_id.id)])
            if obj:
                raise UserError(_('There is already a bucket exist with same bucket status and bucket type'))

    @api.depends('bucket_type_id')
    def _get_value(self):
        for rec in self:
            if rec.bucket_type_id:
                rec.check = True
                rec._get_amount()
            else:
                rec.check = False
                rec._get_amount()

    # def _remove_vendor_line(self):
    #     vendor_line = self.env['vendor.line'].sudo().search([('total_amount_invoiced','=',0),('vendor_line_bucket_id','=',self.id)])
    #     for line in vendor_line:
    #         print(line,"linee")
    #         line.unlink()

    @api.depends('bucket_status')
    def _get_status(self):
        for rec in self:
            if rec.bucket_status == "invoiced" or rec.bucket_status == "billed":
                rec.check2 = True
            else:
                rec.check2 = False


    def _get_amount(self):
        if self.vendor_line:
            self._get_vendor_line_amount()
            self.domain_invoiced_amount()

        if self.vendor_line_released:
            self._get_vendor_line_released_amount()
        if self.user_line:
            self._get_user_line_amount()

        if self.user_line_released:
            self._get_user_line_released_amount()

        if self.vendor_line_released_inside_user:
            self._get_vendor_line_released_inside_user()


    def _get_vendor_line_amount(self):
        for rec in self.vendor_line:
            if self.bucket_status == 'invoiced':
                all_invoices = []
                all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
                    [('budget_inv_vendor_id.id', '=', rec.vendor_id.id)])
                for vendor_inv_line in all_vendor_invoice_lines:
                    all_invoices.append(vendor_inv_line.prod_inv_id)
                all_vendor_invoice_lines_remain = self.env['product.budget.remaining'].sudo().search(
                    [('budget_inv_remaining_vendor_id.id', '=', rec.vendor_id.id)])
                for vendor_inv_remain in all_vendor_invoice_lines_remain:
                    all_invoices.append(vendor_inv_remain.prod_remaining_id)
                all_invoice_number = self.env['product.budget.remaining'].sudo().search(
                    [('prod_remaining_id.id','=',rec.invoice_number.id)])
                for invoice_num_remain in all_invoice_number:
                    all_invoices.append(invoice_num_remain.prod_remaining_id)

                # all_invoices = [invoice_line.prod_inv_id for invoice_line in all_vendor_invoice_lines]
                rem_duplicate_invoice_no_set = set(all_invoices)
                final_invoice_no = list(rem_duplicate_invoice_no_set)
                total_released_amount = 0.0
                total_invoiced_amount = 0.0
                for invoices in final_invoice_no:
                    if invoices.payment_state not in ("paid", "in_payment") and invoices.state == 'posted':
                        total_amount_inv = 0.0
                        total_invoice_amount = 0.0
                        total_amount_rel = 0.0
                        total_invoice_rel = 0.0
                        total_released = 0.0

                        for inv_budget_line in invoices.inv_budget_line:
                            amount_released = 0

                            if not inv_budget_line.released:
                                if inv_budget_line.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_bucket_id.bucket_type_id.id:
                                    if inv_budget_line.amount_residual != inv_budget_line.amount and not inv_budget_line.amount_residual == 0.0:
                                        total_amount_rel += inv_budget_line.amount - inv_budget_line.amount_residual
                                        total_amount_inv += inv_budget_line.amount_residual
                                    elif inv_budget_line.amount_residual == 0.0:
                                        total_amount_inv += inv_budget_line.amount - inv_budget_line.amount_residual
                                        total_amount_rel += inv_budget_line.amount_residual
                                    else:
                                        total_amount_inv += inv_budget_line.amount
                            if inv_budget_line.released:
                                if inv_budget_line.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_bucket_id.bucket_type_id.id:
                                    amount_released += inv_budget_line.amount
                            total_released += amount_released

                        for inv_budget_line in invoices.product_remaining_budget_line:
                            amount_released = 0
                            if not inv_budget_line.released:
                                if inv_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_bucket_id.bucket_type_id.id:
                                    if inv_budget_line.amount_residual != inv_budget_line.amount and not inv_budget_line.amount_residual == 0.0:
                                        total_amount_rel += inv_budget_line.amount - inv_budget_line.amount_residual
                                        total_amount_inv += inv_budget_line.amount_residual
                                    elif inv_budget_line.amount_residual == 0.0:
                                        total_amount_inv += inv_budget_line.amount - inv_budget_line.amount_residual
                                        total_amount_rel += inv_budget_line.amount_residual
                                    else:
                                        total_amount_inv += inv_budget_line.amount
                                if inv_budget_line.prod_remaining_id.id == rec.invoice_number.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_bucket_id.bucket_type_id.id:
                                    if inv_budget_line.amount_residual != inv_budget_line.amount and not inv_budget_line.amount_residual == 0.0:
                                        total_invoice_rel += inv_budget_line.amount - inv_budget_line.amount_residual
                                        total_invoice_amount += inv_budget_line.amount_residual
                                    elif inv_budget_line.amount_residual == 0.0:
                                        total_invoice_amount += inv_budget_line.amount - inv_budget_line.amount_residual
                                        total_invoice_rel += inv_budget_line.amount_residual
                                    else:
                                        total_invoice_amount += inv_budget_line.amount

                            if inv_budget_line.released:
                                if inv_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_bucket_id.bucket_type_id.id:
                                    amount_released += inv_budget_line.amount
                            total_released += amount_released

                        total_released_amount += total_amount_rel + total_released
                        total_invoiced_amount += total_amount_inv
                    rec.write(
                        {'total_amount_released': total_released_amount, "total_amount_invoiced": total_invoiced_amount})

            if self.bucket_status == 'billed':

                total_released_amount = 0.0
                total_invoiced_amount = 0.0
                all_invoices = []
                all_invoice_billed = self.env['account.move'].search([('partner_id','=',rec.vendor_id.id),('move_type','=','in_invoice'),('state','=','posted')])
                for bill_vendor in all_invoice_billed:
                    all_invoices.append(bill_vendor)
                rem_duplicate_invoice_no_set = set(all_invoices)
                final_invoice_no = list(rem_duplicate_invoice_no_set)
                total_released_bill_amount = 0.0
                total_bill_due_amount = 0.0
                total_bill_amount = 0.0
                for invoices in final_invoice_no:
                    if invoices.payment_state not in ("paid", "in_payment",):
                        if invoices.invoice_line_ids:
                            visited_move_line_product = set()
                            for move_line_product in invoices.invoice_line_ids:
                                vendor_bill_bucket = self.env['bucket'].sudo().search(
                                    [('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id),
                                     ('bucket_status', '=', 'billed')])
                                if vendor_bill_bucket.id == self.id and move_line_product.bucket_sub_type.id == rec.sub_bucket_type.id:
                                    visited_move_line_product.add(move_line_product.product_id.id)
                                    if move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                        total_released_bill_amount += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                        total_bill_due_amount += move_line_product.price_subtotal
                                    elif move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                        if move_line_product.bill_residual_amount > 0:
                                            total_released_bill_amount += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                        total_bill_due_amount += move_line_product.bill_residual_amount
                                        total_bill_amount += move_line_product.price_subtotal
                                        if invoices.amount_residual == 0:
                                            total_bill_amount = 0
                                        # if move_line_product.price_unit == invoices.amount_residual and invoices.payment_state != 'partial':
                                        #     print("partial 1")
                                        #     total_released_bill_amount = 0
                                        # if move_line_product.price_unit != invoices.amount_residual and invoices.payment_state != 'partial':
                                        #     print("partial 2")
                                        #     total_released_bill_amount = 0
                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                        total_released_bill_amount += move_line_product.price_subtotal
                                        total_bill_due_amount += move_line_product.price_subtotal
                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                        total_released_bill_amount += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                        total_bill_due_amount += move_line_product.bill_residual_amount
                                        if total_bill_due_amount != 0.0:
                                            total_released_bill_amount = total_bill_due_amount
                    rec.write({'total_amount_released': total_released_bill_amount, "total_amount_invoiced": total_bill_amount-total_released_bill_amount})

    def _get_vendor_line_released_amount(self):
        for rec in self.vendor_line_released:
            if rec.vendor_line_released_bucket_id.bucket_amount == 0.0 or rec.vendor_line_released_bucket_id.bucket_amount == -0.0:
                rec.vendor_line_released_bucket_id.bucket_amount = 0.0

            all_invoices = []
            all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
                [('budget_inv_vendor_id.id', '=', rec.vendor_id.id)])
            for vendor_line_inv in all_vendor_invoice_lines:
                all_invoices.append(vendor_line_inv.prod_inv_id)
            all_vendor_invoice_lines_remain = self.env['product.budget.remaining'].sudo().search(
                [('budget_inv_remaining_vendor_id.id', '=', rec.vendor_id.id)])
            for vendor_inv_remain in all_vendor_invoice_lines_remain:
                all_invoices.append(vendor_inv_remain.prod_remaining_id)
            all_invoice_number = self.env['product.budget.remaining'].sudo().search(
                [('prod_remaining_id.id','=',rec.invoice_number.id)])
            for invoice_number_remain in all_invoice_number:
                all_invoices.append(invoice_number_remain.prod_remaining_id)

            # all_invoices = [invoice_line.prod_inv_id for invoice_line in all_vendor_invoice_lines]
            rem_duplicate_invoice_no_set = set(all_invoices)
            final_invoice_no = list(rem_duplicate_invoice_no_set)
            total_released_amount = 0.0
            total_released_bucket_amount = 0.0
            total_invoiced_amount = 0.0
            total_invoiced_bucket_amount = 0.0
            total_refunded_amount = 0.0
            total_refunded_bucket_amount = 0.0
            for invoices in final_invoice_no:
                total_amount_inv = 0.0
                total_invoice_inv = 0.0
                total_amount_rel = 0.0
                total_invoice_rel = 0.0
                total_amount_ref = 0.0
                total_invoice_ref = 0.0
                if invoices.payment_state != 'not_paid' and invoices.move_type == 'out_invoice':

                    for inv_budget_line in invoices.inv_budget_line:
                        if not inv_budget_line.item_refunded:
                            if inv_budget_line.released:
                                if inv_budget_line.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    total_amount_rel += inv_budget_line.amount
                            else:
                                if inv_budget_line.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    if inv_budget_line.amount_residual != inv_budget_line.amount:
                                        total_amount_rel += inv_budget_line.amount - inv_budget_line.amount_residual
                                        total_amount_inv += inv_budget_line.amount_residual
                                    else:
                                        total_amount_inv += inv_budget_line.amount_residual
                        else:
                            if inv_budget_line.released:
                                if inv_budget_line.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    total_amount_ref += inv_budget_line.amount
                            else:
                                if inv_budget_line.budget_inv_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    if inv_budget_line.refund_residual != inv_budget_line.amount:
                                        total_amount_ref += inv_budget_line.amount - inv_budget_line.refund_residual
                                    else:
                                        total_amount_ref += inv_budget_line.refund_residual

                    for inv_budget_line in invoices.product_remaining_budget_line:
                        if not inv_budget_line.item_refunded:
                            if inv_budget_line.released:
                                if inv_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id and inv_budget_line.budget_inv_remaining_vendor_id.id != False:

                                    total_amount_rel += inv_budget_line.amount
                                if inv_budget_line.prod_remaining_id.id == rec.invoice_number.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    total_invoice_rel += inv_budget_line.amount
                            else:
                                if inv_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    if inv_budget_line.amount_residual != inv_budget_line.amount:
                                        total_amount_rel += inv_budget_line.amount - inv_budget_line.amount_residual
                                        total_amount_inv += inv_budget_line.amount_residual
                                    else:
                                        total_amount_inv += inv_budget_line.amount_residual
                                if inv_budget_line.prod_remaining_id.id == rec.invoice_number.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    if inv_budget_line.amount_residual != inv_budget_line.amount:
                                        total_invoice_rel += inv_budget_line.amount - inv_budget_line.amount_residual
                                        total_invoice_inv += inv_budget_line.amount_residual
                                    else:
                                        total_invoice_inv += inv_budget_line.amount_residual
                        else:
                            if inv_budget_line.released:
                                if inv_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    total_amount_ref += inv_budget_line.amount
                                if inv_budget_line.prod_remaining_id.id == rec.invoice_number.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    total_invoice_ref += inv_budget_line.amount
                            else:
                                if inv_budget_line.budget_inv_remaining_vendor_id.id == rec.vendor_id.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    if inv_budget_line.refund_residual != inv_budget_line.amount:
                                        total_amount_ref += inv_budget_line.amount - inv_budget_line.refund_residual
                                    else:
                                        total_amount_ref += inv_budget_line.refund_residual
                                if inv_budget_line.prod_remaining_id.id == rec.invoice_number.id and inv_budget_line.bucket_type_id.id == rec.vendor_line_released_bucket_id.bucket_type_id.id:
                                    if inv_budget_line.refund_residual != inv_budget_line.amount:
                                        total_invoice_ref += inv_budget_line.amount - inv_budget_line.refund_residual
                                    else:
                                        total_invoice_ref += inv_budget_line.refund_residual

                total_released_amount += total_amount_rel
                total_invoiced_amount += total_amount_inv
                total_refunded_amount += total_amount_ref

                total_released_bucket_amount += total_invoice_rel
                total_invoiced_bucket_amount += total_invoice_inv
                total_refunded_bucket_amount += total_invoice_ref
            if rec.vendor_id.id != False:
                rec.write(
                    {"total_amount_refunded": total_refunded_amount, 'total_amount_released': total_released_amount,
                     "total_amount_invoiced": total_invoiced_amount})

            elif rec.vendor_id.id == False:
                rec.sudo().write({"total_amount_refunded": total_refunded_bucket_amount,'total_amount_released': total_released_bucket_amount,
                     "total_amount_invoiced": total_invoiced_bucket_amount})


            all_bill_lines = self.env['account.move'].sudo().search(
                [('partner_id', '=', rec.vendor_id.id), ('move_type', '=', 'in_invoice')])

            all_bills = [bill_line for bill_line in all_bill_lines]
            rem_duplicate_bill_no_set = set(all_bills)
            final_bill_no = list(rem_duplicate_bill_no_set)
            total_released_bill_amount = 0.0
            total_bill_due_amount = 0.0
            total_bill_amount = 0.0
            for bills in final_bill_no:
                if bills.invoice_line_ids:
                    visited_move_line_product = set()
                    for move_line_product in bills.invoice_line_ids:
                        if move_line_product.bucket_ids.id == self.id:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                total_released_bill_amount += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                total_bill_due_amount += move_line_product.price_subtotal
                            elif move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                total_released_bill_amount += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                total_bill_due_amount += move_line_product.bill_residual_amount
                                total_bill_amount += move_line_product.price_subtotal
                                if bills.amount_residual == 0:
                                    total_bill_amount = 0
                                if total_released_bill_amount == bills.amount_residual and bills.payment_state != 'partial':
                                    total_released_bill_amount = 0
                            elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                total_released_bill_amount += move_line_product.price_subtotal
                                total_bill_due_amount += move_line_product.price_subtotal
                            elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                total_released_bill_amount += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                total_bill_due_amount += move_line_product.bill_residual_amount
            if rec.vendor_id.id != False:
                rec.write(
                    {'total_amount_released': total_released_amount, 'total_amount_bill': total_bill_amount,'total_amount_billed': total_released_bill_amount,
                     "total_amount_billed_due": total_bill_due_amount,
                     "final_amount": total_released_amount - total_released_bill_amount})
            elif rec.vendor_id.id == False:
                rec.write(
                    {'total_amount_released': total_released_bucket_amount, 'total_amount_bill': total_bill_amount,
                     'total_amount_billed': total_released_bill_amount,
                     "total_amount_billed_due": total_bill_due_amount,
                     "final_amount": total_released_bucket_amount - total_released_bill_amount})

            all_refund_bill_lines = self.env['account.move'].sudo().search(
                [('partner_id', '=', rec.vendor_id.id), ('move_type', '=', 'in_refund')])

            all_refunded_bills = [bill_refund_line for bill_refund_line in all_refund_bill_lines]
            rem_duplicate_refund_bill_no_set = set(all_refunded_bills)
            final_refund_bill_no = list(rem_duplicate_refund_bill_no_set)
            total_bill_refund_amount = 0.0
            for refund_bills in final_refund_bill_no:

                if refund_bills.reversed_entry_id.invoice_line_ids:
                    visited_move_line_product = set()
                    for move_line_product_ref in refund_bills.reversed_entry_id.invoice_line_ids:
                        if move_line_product_ref.bucket_ids.id == self.id:
                            visited_move_line_product.add(move_line_product_ref.product_id.id)
                            if move_line_product_ref.product_id.id in visited_move_line_product and move_line_product_ref.refund_residual_amount == 0.0:
                                total_bill_refund_amount += move_line_product_ref.price_subtotal
                            elif move_line_product_ref.product_id.id in visited_move_line_product and move_line_product_ref.refund_residual_amount != move_line_product_ref.price_subtotal:
                                total_bill_refund_amount += move_line_product_ref.price_subtotal - move_line_product_ref.refund_residual_amount

                            elif not move_line_product_ref.product_id.id in visited_move_line_product and move_line_product_ref.refund_residual_amount == 0.0:
                                total_bill_refund_amount += move_line_product_ref.price_subtotal

                            elif not move_line_product_ref.product_id.id in visited_move_line_product and move_line_product_ref.refund_residual_amount != move_line_product_ref.price_subtotal:
                                total_bill_refund_amount += move_line_product_ref.price_subtotal - move_line_product_ref.refund_residual_amount
            rec.write(
                {"total_amount_billed_refund": total_bill_refund_amount,
                 "final_amount": rec.final_amount + total_bill_refund_amount})
            

    def _get_user_line_amount(self):
        for rec in self.user_line:

            all_user_invoice_lines = self.env['product.budget.remaining'].sudo().search(
                [('budget_remaining_user_id.id', '=', rec.user_id.id)])

            all_invoices = [invoice_line.prod_remaining_id for invoice_line in all_user_invoice_lines]

            rem_duplicate_invoice_no_set = set(all_invoices)
            final_invoice_no = list(rem_duplicate_invoice_no_set)
            total_released_amount = 0.0
            total_invoiced_amount = 0.0
            for invoices in final_invoice_no:
                if invoices.payment_state not in ("paid", "in_payment"):
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_released = 0.0
                    inv_budget_line_paid = [inv_budget_line.id for inv_budget_line in invoices.inv_budget_line if
                                            inv_budget_line.released]
                    for product_remaining_budget_line in invoices.product_remaining_budget_line:

                        if len(inv_budget_line_paid) == len(invoices.inv_budget_line):
                            if not product_remaining_budget_line.released:
                                if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.user_line_bucket_id.bucket_type_id.id:
                                    if product_remaining_budget_line.amount_residual != product_remaining_budget_line.amount:
                                        total_amount_rel += product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                        total_amount_inv += product_remaining_budget_line.amount_residual
                                    else:
                                        total_amount_inv += product_remaining_budget_line.amount_residual
                            if product_remaining_budget_line.released:
                                if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.user_line_bucket_id.bucket_type_id.id:
                                    total_released += product_remaining_budget_line.amount
                        else:
                            if not product_remaining_budget_line.released:
                                if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.user_line_bucket_id.bucket_type_id.id:
                                    if product_remaining_budget_line.amount_residual != product_remaining_budget_line.amount:
                                        total_amount_inv += product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                        total_amount_rel += product_remaining_budget_line.amount_residual
                                    else:
                                        total_amount_rel += product_remaining_budget_line.amount_residual
                            if product_remaining_budget_line.released:
                                if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.user_line_bucket_id.bucket_type_id.id:
                                    if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.user_line_bucket_id.bucket_type_id.id:
                                        total_released += product_remaining_budget_line.amount



                    total_released_amount += total_amount_rel + total_released
                    total_invoiced_amount += total_amount_inv
            rec.write(
                {'total_amount_released': total_released_amount, "total_amount_invoiced": total_invoiced_amount})

    def _get_user_line_released_amount(self):
        for rec in self.user_line_released:
            if rec.user_line_released_bucket_id.bucket_amount == 0.0 or rec.user_line_released_bucket_id.bucket_amount == -0.0:
                rec.user_line_released_bucket_id.bucket_amount = 0.0
            all_user_invoice_lines = self.env['product.budget.remaining'].sudo().search(
                [('budget_remaining_user_id.id', '=', rec.user_id.id)])

            all_invoices = [invoice_line.prod_remaining_id for invoice_line in all_user_invoice_lines]

            rem_duplicate_invoice_no_set = set(all_invoices)
            final_invoice_no = list(rem_duplicate_invoice_no_set)
            total_released_amount = 0.0
            total_invoiced_amount = 0.0
            total_refunded_amount = 0.0

            for invoices in final_invoice_no:
                total_amount_inv = 0.0
                total_amount_rel = 0.0
                total_amount_ref = 0.0
                total_released = 0.0
                total_refunded = 0.0
                if invoices.payment_state != 'not_paid':

                    for product_remaining_budget_line in invoices.product_remaining_budget_line:
                        if not product_remaining_budget_line.item_refunded and product_remaining_budget_line.refund_residual == 0.0:
                            if product_remaining_budget_line.released:
                                if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.user_line_released_bucket_id.bucket_type_id.id:
                                    total_amount_rel += product_remaining_budget_line.amount
                            else:

                                if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.user_line_released_bucket_id.bucket_type_id.id:
                                    if product_remaining_budget_line.amount_residual != product_remaining_budget_line.amount and not product_remaining_budget_line.amount_residual == 0.0:

                                        total_amount_rel += product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                        total_amount_inv += product_remaining_budget_line.amount_residual
                                    elif product_remaining_budget_line.amount_residual != product_remaining_budget_line.amount and product_remaining_budget_line.amount_residual == 0.0:

                                        total_amount_rel += product_remaining_budget_line.amount_residual
                                        total_amount_inv += product_remaining_budget_line.amount
                                    else:

                                        total_amount_inv += product_remaining_budget_line.amount_residual

                        else:
                            if product_remaining_budget_line.released and product_remaining_budget_line.item_refunded:
                                if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.user_line_released_bucket_id.bucket_type_id.id:
                                    total_amount_ref += product_remaining_budget_line.amount
                                    total_amount_rel += product_remaining_budget_line.refund_residual
                            else:
                                if product_remaining_budget_line.budget_remaining_user_id.id == rec.user_id.id and product_remaining_budget_line.bucket_type_id.id == rec.user_line_released_bucket_id.bucket_type_id.id:
                                    if product_remaining_budget_line.refund_residual != product_remaining_budget_line.amount:
                                        total_amount_ref += product_remaining_budget_line.amount - product_remaining_budget_line.refund_residual
                                        total_amount_rel += product_remaining_budget_line.refund_residual
                                    else:
                                        total_amount_ref += product_remaining_budget_line.refund_residual
                                        total_amount_rel += product_remaining_budget_line.refund_residual


                    total_released_amount += total_amount_rel + total_released
                    total_invoiced_amount += total_amount_inv
                    total_refunded_amount += total_amount_ref + total_refunded
                    rec.write(
                        {"total_amount_refunded": total_refunded_amount, 'total_amount_released': total_released_amount,
                         "total_amount_invoiced": total_invoiced_amount})
                    

    def _get_vendor_line_released_inside_user(self):
        for rec in self.vendor_line_released_inside_user:
            if rec.vendor_line_released_bucket_id.bucket_amount == 0.0 or rec.vendor_line_released_bucket_id.bucket_amount == -0.0:
                rec.vendor_line_released_bucket_id.bucket_amount = 0.0
            all_bill_lines = self.env['account.move'].sudo().search(
                [('partner_id', '=', rec.vendor_id.id), ('move_type', '=', 'in_invoice')])

            all_bills = [bill_line for bill_line in all_bill_lines]
            rem_duplicate_bill_no_set = set(all_bills)
            final_bill_no = list(rem_duplicate_bill_no_set)
            total_released_bill_amount = 0.0
            total_bill_due_amount = 0.0
            for bills in final_bill_no:
                if bills.invoice_line_ids:
                    visited_move_line_product = set()
                    for move_line_product in bills.invoice_line_ids:
                        visited_move_line_product.add(move_line_product.product_id.id)


                        if move_line_product.bucket_ids.bucket_type_id.id == self.bucket_type_id.id:

                            if move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                total_released_bill_amount += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                total_bill_due_amount += move_line_product.price_subtotal
                            elif move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                total_released_bill_amount += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                total_bill_due_amount += move_line_product.bill_residual_amount
                            elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                total_released_bill_amount += move_line_product.price_subtotal
                                total_bill_due_amount += move_line_product.price_subtotal
                            elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                total_released_bill_amount += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                total_bill_due_amount += move_line_product.bill_residual_amount

            rec.write({'total_amount_billed': total_released_bill_amount,
                       "total_amount_billed_due": total_bill_due_amount, "final_amount": -total_released_bill_amount})

            all_bill_ref_lines = self.env['account.move'].sudo().search(
                [('partner_id', '=', rec.vendor_id.id), ('move_type', '=', 'in_refund')])

            all_ref_bills = [bill_line for bill_line in all_bill_ref_lines]
            rem_duplicate_ref_bill_no_set = set(all_ref_bills)
            final_bill_ref_no = list(rem_duplicate_ref_bill_no_set)
            total_ref_bill_amount = 0.0
            for bills in final_bill_ref_no:
                if bills.reversed_entry_id.invoice_line_ids:
                    visited_ref_move_line_product = set()
                    for move_line_product in bills.reversed_entry_id.invoice_line_ids:
                        visited_ref_move_line_product.add(move_line_product.product_id.id)
                        if move_line_product.bucket_ids.bucket_type_id.id == self.bucket_type_id.id:
                            if move_line_product.product_id.id in visited_ref_move_line_product and move_line_product.refund_residual_amount == move_line_product.price_subtotal:
                                total_ref_bill_amount += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                            elif move_line_product.product_id.id in visited_ref_move_line_product and move_line_product.refund_residual_amount != move_line_product.price_subtotal:
                                total_ref_bill_amount += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                            elif not move_line_product.product_id.id in visited_ref_move_line_product and move_line_product.refund_residual_amount == move_line_product.price_subtotal:
                                total_ref_bill_amount += move_line_product.price_subtotal
                            elif not move_line_product.product_id.id in visited_ref_move_line_product and move_line_product.refund_residual_amount != move_line_product.price_subtotal:
                                total_ref_bill_amount += move_line_product.price_subtotal - move_line_product.refund_residual_amount
            rec.write({'total_amount_refunded': total_ref_bill_amount,
                       })

    def domain_invoiced_amount(self):
        if self.vendor_line:
            self.vendor_line = [(6, 0, self.env['vendor.line'].search([('total_amount_invoiced', '>', 0.0),('vendor_line_bucket_id','=',self.id)]).ids)]




class VendorLine(models.Model):
    _name = "vendor.line"

    vendor_id = fields.Many2one('res.partner','Vendors')
    vendor_line_bucket_id = fields.Many2one('bucket','bucket')
    total_amount_released = fields.Float('Inv. Released')
    total_amount_invoiced = fields.Float('Amount')
    total_amount_billed = fields.Float('Bill Released')
    total_amount_billed_due = fields.Float('Bill Due')
    bucket_status_billed = fields.Selection(related='vendor_line_bucket_id.bucket_status')
    sub_bucket_type = fields.Many2one('bucket.type','Sub Bucket Type')
    invoice_number = fields.Many2one('account.move','Invoice Number')

    def fetch_vendor_unpaid_invoice_details(self,final_invoice_no):
        for invoices in final_invoice_no:
            if invoices.state == 'posted':
                if invoices.payment_state == 'partial':
                    print(invoices.id,"partial")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_invoice_rel = 0.0
                    total_paid_amount_rel = 0.0
                    total_invoice_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id and inv_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id:
                            total_paid_amount_inv += inv_budget_line.amount_residual
                            total_amount_inv += inv_budget_line.amount
                            exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                [('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                 ('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                 ('bucket_sub_type', '=', False)])

                            if not exist_invoice_number:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {'vendor_id': self.vendor_id.id, 'invoice_name': invoices.id,
                                     'bucket_type_id': inv_budget_line.bucket_type_id.id,
                                     'vendor_inv_amount': inv_budget_line.amount,
                                     'vendor_amount_invoiced': inv_budget_line.amount_residual,
                                     'vendor_amount_released': inv_budget_line.amount - inv_budget_line.amount_residual,
                                     'partial_due_amount': inv_budget_line.amount_residual,
                                     'partial_paid_amount': inv_budget_line.amount - inv_budget_line.amount_residual
                                     })
                            else:
                                exist_invoice_number.write(
                                    {'vendor_inv_amount': inv_budget_line.amount,
                                     'vendor_amount_invoiced': inv_budget_line.amount_residual,
                                     'vendor_amount_released': inv_budget_line.amount - inv_budget_line.amount_residual,
                                     'partial_due_amount': inv_budget_line.amount_residual,
                                     'partial_paid_amount': inv_budget_line.amount - inv_budget_line.amount_residual})
                    all_fixed_amount_released = []
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(invoices.inv_budget_line):
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id == False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),('bucket_sub_type', '=', False)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': total_paid_invoice_rel,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    exist_invoice_number.write(
                                        {'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                            if product_remaining_budget_line.prod_remaining_id.id == self.invoice_number.id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': False, 'invoice_name': invoices.id,'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    exist_invoice_number.write({'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id),('vendor_id', '=', self.vendor_id.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': self.vendor_id.id, 'invoice_name': invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual,'partial_due_amount':product_remaining_budget_line.amount_residual,
                                        'partial_paid_amount':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual
                                    })
                                else:
                                    exist_invoice_number.write({'vendor_inv_amount':product_remaining_budget_line.amount,'vendor_amount_invoiced':product_remaining_budget_line.amount_residual,'vendor_amount_released':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual,
                                                                'partial_due_amount':product_remaining_budget_line.amount_residual,'partial_paid_amount':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual})
                    else:
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id == False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                    [('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', False)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create(
                                        {'vendor_id': self.vendor_id.id, 'invoice_name': invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': total_paid_invoice_rel,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    exist_invoice_number.write(
                                        {'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                            if product_remaining_budget_line.prod_remaining_id.id == self.invoice_number.id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                    [('invoice_name', '=', invoices.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create(
                                        {'vendor_id': False, 'invoice_name': invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                         'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    exist_invoice_number.write(
                                        {'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                    [('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create(
                                        {'vendor_id': self.vendor_id.id, 'invoice_name': invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                         'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    exist_invoice_number.write(
                                        {'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                    total_vendor_paid_amount = total_amount_inv + total_invoice_rel
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_invoice_rel
                    vendor_lst_inv = []
                    vendor_lst_rel = []
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and inv_budget_line.budget_inv_vendor_id.id == self.vendor_id.id:
                            vendor_lst_inv.append(inv_budget_line.budget_inv_vendor_id.id)
                    for product_remaining_budget_line in invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.budget_inv_remaining_vendor_id.id == self.vendor_id.id and product_remaining_budget_line.sub_bucket_type.id == False:
                            vendor_lst_rel.append(product_remaining_budget_line.budget_inv_remaining_vendor_id.id)

                    if len(vendor_lst_rel) == len(vendor_lst_inv) and len(vendor_lst_inv) > 0 and len(vendor_lst_rel) > 0:
                        existing_record_1 = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id),('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_bucket_id.bucket_type_id.id),('bucket_sub_type','=',False)])

                        if total_vendor_amount_part_paid_per_invoice != 0.0:
                            if existing_record_1:
                                existing_record_1.write({'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                            else:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_bucket_id.bucket_type_id.id,'vendor_inv_amount':total_vendor_paid_amount,
                                     'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})
                        else:
                            if existing_record_1:
                                existing_record_1.write({'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                            else:
                                self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_bucket_id.bucket_type_id.id,'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                else:
                    if not invoices.payment_state == 'posted':
                        total_vendor_amount = 0.0
                        total_amount_inv = 0.0
                        total_amount_rel = 0.0
                        for inv_budget_line in invoices.inv_budget_line:
                            if inv_budget_line.budget_inv_vendor_id in self.vendor_id and inv_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id:
                                total_amount_inv += inv_budget_line.amount
                                existing_record = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('vendor_id','=',self.vendor_id.id),('bucket_type_id','=',self.vendor_line_bucket_id.bucket_type_id.id)])
                                if not existing_record:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,
                                         "bucket_type_id": self.vendor_line_bucket_id.bucket_type_id.id,'vendor_amount_invoiced': total_amount_inv,'vendor_inv_amount': total_amount_inv})
                                else:
                                    existing_record.write({'vendor_amount_invoiced':total_amount_inv,'vendor_inv_amount':total_amount_inv})

                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id == False:
                                existing_record = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),('bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id)])
                                if not existing_record:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,"bucket_type_id": self.vendor_line_bucket_id.bucket_type_id.id,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount,'vendor_inv_amount': product_remaining_budget_line.amount})
                                else:
                                    vendor_prod_amount = existing_record.vendor_amount_invoiced + product_remaining_budget_line.amount
                                    # existing_record.write({'vendor_amount_invoiced': vendor_prod_amount,'vendor_inv_amount': vendor_prod_amount})
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id.id == False and product_remaining_budget_line.sub_bucket_type.id != False and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id:
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': False, 'invoice_name': invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount,'vendor_inv_amount': product_remaining_budget_line.amount})
                                else:
                                    exist_inv_amount = exist_invoice_number.vendor_amount_invoiced + product_remaining_budget_line.amount
                                    # exist_invoice_number.write({'vendor_amount_invoiced': exist_inv_amount,'vendor_inv_amount': exist_inv_amount})

                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:
                                existing_record = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not existing_record:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                        'vendor_amount_invoiced': product_remaining_budget_line.amount,'vendor_inv_amount': product_remaining_budget_line.amount})
                                else:
                                    vendor_prod_amount = existing_record.vendor_amount_invoiced + product_remaining_budget_line.amount
                                    # existing_record.write({'vendor_amount_invoiced': vendor_prod_amount,'vendor_inv_amount': vendor_prod_amount})

                        # total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                        # print(total_vendor_amount_per_invoice,"<totlll")

                        # for product_invoice_line in invoices.product_remaining_budget_line:
                        #     if product_invoice_line.budget_inv_remaining_vendor_id.id == False and product_invoice_line.sub_bucket_type.id != False:
                        #         print("shi")
                        #         exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),
                        #                                                                                ('bucket_type_id','=',product_invoice_line.bucket_type_id.id),
                        #                                                                                ('bucket_sub_type','=',product_invoice_line.sub_bucket_type.id)])
                        #         print(exist_invoice_number,"rexxxx")
                        #         if not exist_invoice_number:
                        #             print("createdd")
                        #             create_record = self.env['vendor.invoice.detail'].sudo().create(
                        #                 {'vendor_id': False, 'invoice_name': invoices.id,'bucket_type_id': product_invoice_line.bucket_type_id.id,
                        #                  'bucket_sub_type':product_invoice_line.sub_bucket_type.id,'vendor_amount_invoiced': product_invoice_line.amount,
                        #                  'vendor_inv_amount': product_invoice_line.amount})
                        #         else:
                        #             print(exist_invoice_number,"elseeee")
                        #             exist_inv_amount = exist_invoice_number.vendor_amount_invoiced + product_invoice_line.amount
                        #             exist_invoice_number.write({'vendor_amount_invoiced':exist_inv_amount,'vendor_inv_amount':exist_inv_amount})
                        #
                        #     if product_invoice_line.budget_inv_remaining_vendor_id in self.vendor_id and product_invoice_line.sub_bucket_type.id == False:
                        #         existing_record = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('vendor_id','=',self.vendor_id.id),('bucket_type_id','=',self.vendor_line_bucket_id.bucket_type_id.id)])
                        #         print(existing_record,"xx reddd")
                        #         if not existing_record:
                        #             print("ifff")
                        #             create_record = self.env['vendor.invoice.detail'].sudo().create({"vendor_id":self.vendor_id.id,'invoice_name':invoices.id,"bucket_type_id":self.vendor_line_bucket_id.bucket_type_id.id,
                        #                                                                      'vendor_amount_invoiced':total_vendor_amount_per_invoice,'vendor_inv_amount':total_vendor_amount_per_invoice})
                        #         else:
                        #             print("elseee>><><><>")
                        #             existing_record.write({'vendor_amount_invoiced':total_vendor_amount_per_invoice,'vendor_inv_amount':total_vendor_amount_per_invoice})

    def fetch_vendor_paid_invoice_details(self,final_paid_invoice_no):
        for paid_invoices in final_paid_invoice_no:
            if paid_invoices.state == 'posted':
                if paid_invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id and inv_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id:
                            total_paid_amount_inv += inv_budget_line.amount_residual
                            total_amount_inv += inv_budget_line.amount

                    all_fixed_amount_released = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(paid_invoices.inv_budget_line):
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id == False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),('bucket_sub_type', '=', False)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': self.vendor_id.id, 'invoice_name': paid_invoices.id,'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    if product_remaining_budget_line.amount_residual > 0:
                                        exist_invoice_number.write(
                                            {'released':False,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                             'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': product_remaining_budget_line.amount_residual,
                                             'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                                    else:
                                        exist_invoice_number.write({'released': True,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                             'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': product_remaining_budget_line.amount_residual,
                                             'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                            if product_remaining_budget_line.prod_remaining_id.id == self.invoice_number.id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', paid_invoices.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': False,'invoice_name': paid_invoices.id,'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    if product_remaining_budget_line.amount_residual > 0:
                                        print("relese false")
                                        exist_invoice_number.write(
                                            { 'vendor_inv_amount': product_remaining_budget_line.amount,'released':False,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                             'partial_due_amount': product_remaining_budget_line.amount_residual,'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                                    else:
                                        exist_invoice_number.write(
                                            {'vendor_inv_amount': product_remaining_budget_line.amount,'released': True,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                             'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                             'partial_due_amount': product_remaining_budget_line.amount_residual,'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', paid_invoices.id),('vendor_id', '=', self.vendor_id.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': self.vendor_id.id, 'invoice_name': paid_invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual,'partial_due_amount':product_remaining_budget_line.amount_residual,
                                        'partial_paid_amount':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual
                                    })
                                else:
                                    if product_remaining_budget_line.amount_residual >0:
                                        exist_invoice_number.write({'released':False,'vendor_inv_amount':product_remaining_budget_line.amount,'vendor_amount_invoiced':product_remaining_budget_line.amount_residual,'vendor_amount_released':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual,
                                                                    'partial_due_amount':product_remaining_budget_line.amount_residual,'partial_paid_amount':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual})
                                    else:
                                        exist_invoice_number.write({'released': True,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                                                    'partial_due_amount': product_remaining_budget_line.amount_residual,'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                    else:

                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id == False:
                                print("ss")
                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                            if product_remaining_budget_line.prod_remaining_id.id == self.invoice_number.id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                    [('invoice_name', '=', paid_invoices.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create(
                                        {'vendor_id': False, 'invoice_name': paid_invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                         'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                    [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])

                                if not exist_invoice_number:

                                    create_record = self.env['vendor.invoice.detail'].sudo().create(
                                        {'vendor_id': self.vendor_id.id, 'invoice_name': paid_invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                         'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })

                    total_vendor_paid_amount = total_amount_inv
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv
                    vendor_lst_inv = []
                    vendor_lst_rel = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and inv_budget_line.budget_inv_vendor_id.id == self.vendor_id.id:
                            vendor_lst_inv.append(inv_budget_line.budget_inv_vendor_id.id)
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.bucket_type_id.id == self.vendor_line_bucket_id.bucket_type_id.id and product_remaining_budget_line.budget_inv_remaining_vendor_id.id == self.vendor_id.id and product_remaining_budget_line.sub_bucket_type.id == False:
                            vendor_lst_rel.append(product_remaining_budget_line.budget_inv_remaining_vendor_id.id)

                    if len(vendor_lst_rel) == len(vendor_lst_inv) and len(vendor_lst_inv) > 0 and len(vendor_lst_rel) > 0:
                        existing_record_1 = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', paid_invoices.id),('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_bucket_id.bucket_type_id.id),('bucket_sub_type','=',False)])

                        if total_vendor_amount_part_paid_per_invoice != 0.0:
                            if existing_record_1:
                                existing_record_1.write({'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                            else:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,'bucket_type_id':self.vendor_line_bucket_id.bucket_type_id.id,'vendor_inv_amount':total_vendor_paid_amount,
                                     'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})
                        else:
                            if existing_record_1:
                                existing_record_1.write({'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                            else:
                                self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,'bucket_type_id':self.vendor_line_bucket_id.bucket_type_id.id,'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                    # for inv_budget_line in paid_invoices.inv_budget_line:
                    #     if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                    #         total_paid_amount_inv += inv_budget_line.amount_residual
                    #         total_amount_inv += inv_budget_line.amount
                    # all_fixed_amount_released_paid = []
                    # for inv_budget_line in paid_invoices.inv_budget_line:
                    #     if inv_budget_line.released:
                    #         all_fixed_amount_released_paid.append(inv_budget_line.id)
                    # if len(all_fixed_amount_released_paid) == len(paid_invoices.inv_budget_line):
                    #     for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                    #         if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.sub_bucket_type.id == False:
                    #             print("vendor not sub bucket")
                    #             total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    #             total_amount_rel += product_remaining_budget_line.amount
                    #         if product_remaining_budget_line.budget_inv_remaining_vendor_id.id == False and product_remaining_budget_line.sub_bucket_type.id != False:
                    #             print("sub bucket")
                    #             total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    #             total_amount_rel += product_remaining_budget_line.amount
                    #         if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.sub_bucket_type.id != False:
                    #             print("vendor sub bucket")
                    #             total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    #             total_amount_rel += product_remaining_budget_line.amount
                    #             existing_vendor_bucket = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', self.invoice_number.id), ('vendor_id', '=', self.vendor_id.id),
                    #                  ('bucket_sub_type','=',product_remaining_budget_line.sub_bucket_type.id),('bucket_type_id','=',product_remaining_budget_line.bucket_type_id.id)])
                    #             print(existing_vendor_bucket,"existing vendor bucket")
                    #             if not existing_vendor_bucket:
                    #                 print("not existing")
                    #                 create_partial = self.env['vendor.invoice.detail'].sudo().create({'invoice_name':product_remaining_budget_line.prod_remaining_id.id,'vendor_id':self.vendor_id.id,
                    #                                                                                   'bucket_type_id':self.vendor_line_bucket_id.bucket_type_id.id,
                    #                                                                                   'bucket_sub_type':product_remaining_budget_line.bucket_type_id.id,
                    #                                                                                   'vendor_amount_invoiced':product_remaining_budget_line.amount_residual,
                    #                                             'vendor_amount_released':product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                    #                                             'vendor_inv_amount':product_remaining_budget_line.amount})
                    #                 print(create_partial,"part create")
                    #             else:
                    #                 existing_vendor_bucket.write({'vendor_amount_invoiced':product_remaining_budget_line.amount_residual,
                    #                                             'vendor_amount_released':product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                    #                                             'vendor_inv_amount':product_remaining_budget_line.amount})
                    #                 print(existing_vendor_bucket,"writeee")
                    #
                    # else:
                    #     print("else m aaya")
                    #     for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                    #         if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.sub_bucket_type.id == False:
                    #             total_paid_amount_rel += product_remaining_budget_line.amount
                    #             total_amount_rel += product_remaining_budget_line.amount
                    #         if product_remaining_budget_line.budget_inv_remaining_vendor_id.id == False and product_remaining_budget_line.sub_bucket_type.id != False:
                    #             total_paid_amount_rel += product_remaining_budget_line.amount
                    #             total_amount_rel += product_remaining_budget_line.amount
                    #
                    # total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    # total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    # existing_record_1 = self.env['vendor.invoice.detail'].sudo().search(
                    #     [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id)])
                    # print(existing_record_1,"111")

                    # if total_vendor_amount_part_paid_per_invoice != 0.0:
                    #     if existing_record_1:
                    #         existing_record_1.write(
                    #             {'vendor_amount_invoiced': total_vendor_amount_part_paid_per_invoice,
                    #              'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                    #              'partial_due_amount': total_vendor_amount_part_paid_per_invoice,
                    #              'partial_paid_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                    #              'vendor_inv_amount':total_vendor_paid_amount})
                    #     else:
                    #         create_record = self.env['vendor.invoice.detail'].sudo().create(
                    #             {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                    #              'bucket_type_id': self.vendor_line_bucket_id.bucket_type_id.id,
                    #              'vendor_amount_invoiced': total_vendor_amount_part_paid_per_invoice,
                    #              'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                    #              'partial_due_amount': total_vendor_amount_part_paid_per_invoice,
                    #              'partial_paid_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                    #              'vendor_inv_amount':total_vendor_paid_amount})
                    #
                    # else:
                    #     if existing_record_1:
                    #         existing_record_1.write(
                    #             {'released': True, 'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                    #              'partial_paid_amount': 0.0,
                    #              'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                    #              'vendor_inv_amount':total_vendor_paid_amount})
                    #     else:
                    #         self.env['vendor.invoice.detail'].sudo().create(
                    #             {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                    #              'bucket_type_id': self.vendor_line_bucket_id.bucket_type_id.id, 'released': True,
                    #              'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                    #              'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                    #              'vendor_inv_amount':total_vendor_paid_amount})
                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                         ('bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id)])
                    if not existing_record:
                        create_record = self.env['vendor.invoice.detail'].sudo().create(
                            {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                             "bucket_type_id": self.vendor_line_bucket_id.bucket_type_id.id,

                             'vendor_amount_released': total_vendor_amount_per_invoice,
                             'vendor_amount_invoiced': 0.0,
                             'vendor_inv_amount':total_vendor_amount_per_invoice})
                    else:
                        existing_record.write({'vendor_amount_released': total_vendor_amount_per_invoice,
                             'vendor_amount_invoiced': 0.0,'vendor_inv_amount':total_vendor_amount_per_invoice})

    def fetch_vendor_bill_details(self):
        fetch_bills = self.env['account.move'].sudo().search([('move_type', '=', "in_invoice")])
        fetch_refunded_bills = self.env['account.move'].sudo().search([('move_type', '=', "in_refund")])
        self.fetch_vendor_paid_bills(fetch_bills)
        self.fetch_vendor_refunded_bills(fetch_refunded_bills)
        domain = [('vendor_id', '=', self.vendor_id.id), ("debit", '=', False),('bill_name.payment_state','not in',('paid','in_payment')),
                  ('bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id),('bucket_sub_type','=',self.sub_bucket_type.id)]

        vals = {
            'name': _('Bill Detail'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'vendor.bill.detail',
        }
        return vals

    def fetch_vendor_paid_bills(self, fetch_bills):
        for record in fetch_bills:
            if record.partner_id.id == self.vendor_id.id:
                if record.state == 'posted' and record.payment_state == 'not_paid':
                    if record.invoice_line_ids:
                        visited_move_line_product = set()
                        for move_line_product in record.invoice_line_ids:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.product_id:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                    limit=1, order="id desc")
                                vendor_id = vendor_id.partner_id
                            else:
                                vendor_id = self.vendor_id
                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                 ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id),
                                 ('bucket_sub_type','=',move_line_product.bucket_sub_type.id)])
                            total_amount_paid = 0
                            for move_line_product in record.invoice_line_ids:
                                if move_line_product.product_id.id in visited_move_line_product:
                                    total_amount_paid += move_line_product.price_subtotal
                                else:
                                    total_amount_paid = move_line_product.price_subtotal
                            if not existing_bill_rec:
                                self.env['vendor.bill.detail'].sudo().create({
                                    'bill_name': record.id,
                                    'vendor_id': vendor_id.id,
                                    'vendor_amount_due': total_amount_paid,
                                    'vendor_amount_bill': total_amount_paid,
                                    'bill_paid': True,
                                    'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                    'bucket_sub_type':move_line_product.bucket_sub_type.id
                                })
                            else:
                                existing_bill_rec.write({
                                    'vendor_amount_bill': 0.0,
                                    'vendor_amount_due': total_amount_paid,
                                    'bill_paid': True,
                                })

                if record.state == 'posted' and record.payment_state in ("paid", "in_payment"):
                    if record.invoice_line_ids:
                        visited_move_line_product = set()
                        for move_line_product in record.invoice_line_ids:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.product_id:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                    limit=1, order="id desc")
                                vendor_id = vendor_id.partner_id
                            else:
                                vendor_id = self.vendor_id
                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                 ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id),
                                 ('bucket_sub_type','=',move_line_product.bucket_sub_type.id or None)])
                            total_amount_paid = 0
                            for move_line_product in record.invoice_line_ids:
                                if move_line_product.product_id.id in visited_move_line_product:
                                    total_amount_paid += move_line_product.price_subtotal
                                else:
                                    total_amount_paid = move_line_product.price_subtotal
                            if not existing_bill_rec:
                                self.env['vendor.bill.detail'].sudo().create({
                                    'bill_name': record.id,
                                    'vendor_id': vendor_id.id,
                                    'vendor_amount_paid': total_amount_paid,
                                    'bill_paid': True,
                                    'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                    'bucket_sub_type': move_line_product.bucket_sub_type.id or None
                                })
                            else:
                                existing_bill_rec.write({
                                    'vendor_amount_bill': 0.0,
                                    'vendor_amount_paid': total_amount_paid,
                                    'bill_paid': True,
                                })

                if record.state == 'posted' and record.payment_state == 'partial':
                    if record.invoice_line_ids:
                        visited_move_line_product = set()
                        total_amount_paid = 0
                        remaining_bill_amount = 0
                        for move_line_product in record.invoice_line_ids:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.bill_residual_amount != 0.0:
                                if not move_line_product.is_bill_paid:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1, order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                         ('bucket_type_id', '=',move_line_product.bucket_ids.bucket_type_id.id),
                                         ('bucket_sub_type','=',move_line_product.bucket_sub_type.id or None)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id),('id','=',self.id)])

                                    if move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                        remaining_bill_amount += move_line_product.price_subtotal
                                    elif move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                        remaining_bill_amount += move_line_product.bill_residual_amount
                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal
                                        remaining_bill_amount += move_line_product.price_subtotal

                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                        remaining_bill_amount += move_line_product.bill_residual_amount

                                    if not existing_bill_rec:

                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': remaining_bill_amount,
                                            'vendor_line_billed_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': total_amount_paid,
                                            'vendor_amount_due': total_amount_paid + remaining_bill_amount,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                            'bucket_sub_type': move_line_product.bucket_sub_type.id or None
                                        })
                                    else:
                                        existing_bill_rec.write({'vendor_amount_paid': total_amount_paid,
                                                                 'vendor_amount_bill': remaining_bill_amount,
                                                                 'bill_paid': move_line_product.is_bill_paid})
                                else:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1, order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                         ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id),
                                         ('bucket_sub_type','=',move_line_product.bucket_sub_type.id or None)])

                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    total_amount_paid = 0
                                    if move_line_product.product_id.id in visited_move_line_product and move_line_product.is_partial:
                                        total_amount_paid += move_line_product.price_subtotal
                                    elif move_line_product.is_partial and not move_line_product.is_bill_paid:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_billed_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': total_amount_paid,
                                            'vendor_amount_due': total_amount_paid,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                            'bucket_sub_type': move_line_product.bucket_sub_type.id or None
                                        })
                                    else:
                                        existing_bill_rec.write({'vendor_amount_paid': total_amount_paid,
                                                                 'bill_paid': move_line_product.is_bill_paid})
                            else:
                                if move_line_product.is_bill_paid:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1,
                                            order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                         ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id),
                                         ('bucket_sub_type','=',move_line_product.bucket_sub_type.id or None)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_billed_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': move_line_product.price_subtotal,
                                            'vendor_amount_due': move_line_product.price_subtotal,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                            'bucket_sub_type': move_line_product.bucket_sub_type.id or None
                                        })
                                    else:
                                        existing_bill_rec.write({
                                            'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                            'vendor_amount_bill': 0.0,
                                            'bill_paid': move_line_product.is_bill_paid, })

    def fetch_vendor_refunded_bills(self, fetch_refunded_bills):
        for record in fetch_refunded_bills:
            if record.partner_id.id == self.vendor_id.id:
                if record.state == 'posted' and record.payment_state in ("paid", "in_payment"):
                    if record.invoice_line_ids:
                        visited_move_line_product = set()
                        for move_line_product in record.invoice_line_ids:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.product_id:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                    limit=1, order="id desc")
                                vendor_id = vendor_id.partner_id
                            else:
                                vendor_id = self.vendor_id
                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                [('bill_name', '=', record.reversed_entry_id.id), ('vendor_id', '=', vendor_id.id),
                                 ('bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id)])
                            vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id), (
                            'vendor_line_bucket_id', '=',
                            self.vendor_line_bucket_id.bucket_type_id.id)])
                            total_amount_refunded = 0
                            for move_line_product in record.invoice_line_ids:
                                if move_line_product.product_id.id in visited_move_line_product:
                                    total_amount_refunded += move_line_product.price_subtotal
                                else:
                                    total_amount_refunded = move_line_product.price_subtotal

                            if not existing_bill_rec:
                                self.env['vendor.bill.detail'].sudo().create({
                                    'bill_name': record.reversed_entry_id.id,
                                    'vendor_id': vendor_id.id,
                                    # 'vendor_amount_bill':move_line_product.price_subtotal,
                                    'vendor_line_released_id': vendor_line_released_id.id,
                                    'vendor_bill_amount_refunded': total_amount_refunded,
                                    'vendor_amount_paid': total_amount_refunded,
                                    'bill_paid': True,
                                    'bucket_type_id': self.vendor_line_bucket_id.bucket_type_id.id
                                })
                            else:
                                existing_bill_rec.write({
                                    'vendor_amount_bill': 0.0,
                                    'vendor_bill_amount_refunded': total_amount_refunded,
                                    'bill_paid': True,
                                })
                if record.state == 'posted' and record.payment_state == 'partial':
                    if record.reversed_entry_id.invoice_line_ids:
                        visited_move_line_product = set()
                        total_amount_paid = 0
                        remaining_bill_amount = 0
                        total_refund = 0
                        for move_line_product in record.reversed_entry_id.invoice_line_ids:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.bill_residual_amount != 0.0:
                                if not move_line_product.is_bill_paid:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1, order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.reversed_entry_id.id),
                                         ('vendor_id', '=', vendor_id.id),
                                         (
                                         'bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])

                                    if move_line_product.product_id.id in visited_move_line_product and move_line_product.refund_residual_amount == move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                                        remaining_bill_amount += move_line_product.price_subtotal
                                    elif move_line_product.product_id.id in visited_move_line_product and move_line_product.refund_residual_amount != move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                                        remaining_bill_amount += move_line_product.refund_residual_amount
                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.refund_residual_amount == move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal
                                        remaining_bill_amount += move_line_product.price_subtotal

                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.refund_residual_amount != move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                                        remaining_bill_amount += move_line_product.refund_residual_amount
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': remaining_bill_amount,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': total_amount_paid,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': self.vendor_line_bucket_id.bucket_type_id.id
                                        })
                                    else:
                                        existing_bill_rec.write({'vendor_amount_paid': total_amount_paid,
                                                                 'vendor_amount_bill': remaining_bill_amount,
                                                                 'bill_paid': move_line_product.is_bill_paid})
                                else:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1, order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                         (
                                         'bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    total_amount_paid = 0
                                    if move_line_product.product_id.id in visited_move_line_product and move_line_product.is_partial:
                                        total_amount_paid += move_line_product.price_subtotal
                                    elif move_line_product.is_partial and not move_line_product.is_bill_paid:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': total_amount_paid,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': self.vendor_line_bucket_id.bucket_type_id.id
                                        })
                                    else:
                                        existing_bill_rec.write({'vendor_amount_paid': total_amount_paid,
                                                                 'bill_paid': move_line_product.is_bill_paid})
                            else:
                                if move_line_product.is_bill_refunded:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1,
                                            order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.reversed_entry_id.id),
                                         ('vendor_id', '=', vendor_id.id),
                                         (
                                         'bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.reversed_entry_id.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': move_line_product.price_subtotal,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': self.vendor_line_bucket_id.bucket_type_id.id
                                        })
                                    else:
                                        existing_bill_rec.write({
                                            'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                            'vendor_amount_bill': 0.0,
                                            'bill_paid': move_line_product.is_bill_paid, })
                                else:
                                    total_refund += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1,
                                            order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.reversed_entry_id.id),
                                         ('vendor_id', '=', vendor_id.id),
                                         (
                                         'bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.reversed_entry_id.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': move_line_product.price_subtotal,
                                            'vendor_bill_amount_refunded': total_refund,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': self.vendor_line_bucket_id.bucket_type_id.id
                                        })
                                    else:
                                        existing_bill_rec.write({
                                            'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_bill_amount_refunded': total_refund,
                                            'bill_paid': move_line_product.is_bill_paid, })

    def fetch_vendor_invoice_details(self):
        all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_inv_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False)])
        all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_inv_remaining_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False)])
        all_invoice_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('prod_remaining_id', '=', self.invoice_number.id), ('released', '=', False)])

        all_invoices = []
        for invoice_line in all_vendor_invoice_lines:
            all_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_vendor_remaining_lines:
            all_invoices.append(remaining_inv_line.prod_remaining_id)
        for remaining_inv_number in all_invoice_remaining_lines:
            all_invoices.append(remaining_inv_number.prod_remaining_id)
        rem_duplicate_invoice_no_set = set(all_invoices)
        final_invoice_no = list(rem_duplicate_invoice_no_set)
        self.fetch_vendor_unpaid_invoice_details(final_invoice_no)
        all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_inv_vendor_id.id', '=', self.vendor_id.id), ('released', '=', True)])
        all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_inv_remaining_vendor_id.id', '=', self.vendor_id.id), ('released', '=', True)])
        all_invoice_remain_lines = self.env['product.budget.remaining'].sudo().search(
            [('prod_remaining_id', '=', self.invoice_number.id), ('released', '=', True)])

        all_paid_invoices = []

        for invoice_line in all_vendor_invoice_lines:
            all_paid_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_vendor_remaining_lines:
            all_paid_invoices.append(remaining_inv_line.prod_remaining_id)
        for remaining_inv_number in all_invoice_remain_lines:
            all_paid_invoices.append(remaining_inv_number.prod_remaining_id)

        rem_duplicate_paid_invoice_no_set = set(all_paid_invoices)
        final_paid_invoice_no = list(rem_duplicate_paid_invoice_no_set)
        self.fetch_vendor_paid_invoice_details(final_paid_invoice_no)
        if not self.invoice_number:
            return {
                'name': _('Details'),
                'domain': [('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_bucket_id.bucket_type_id.id),('released','=',False),('vendor_amount_invoiced','>',0.0)],
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'target':'new',
                'res_model': 'vendor.invoice.detail',
            }
        else:
            return {
                'name': _('Details'),
                'domain': [('vendor_id', '=', self.vendor_id.id),('invoice_name','=',self.invoice_number.id),
                           ('bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id),
                           ('released', '=', False), ('vendor_amount_invoiced', '>', 0.0)],
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'target': 'new',
                'res_model': 'vendor.invoice.detail',
            }

class VendorLineReleased(models.Model):
    _name = "vendor.line.released"

    vendor_id = fields.Many2one('res.partner', 'Vendors')
    vendor_line_released_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount_refunded = fields.Float('Refunded')
    total_amount_released = fields.Float('Inv. Released')
    total_amount_invoiced = fields.Float('Inv. Due')
    total_amount_billed = fields.Float('Bill Released')
    total_amount_bill = fields.Float('Billed')
    total_amount_billed_due = fields.Float('Bill Due')
    total_amount_billed_refund = fields.Float('Bill Refunded')
    final_amount = fields.Float("Final Amount")
    sub_bucket_type = fields.Many2one('bucket.type', 'Sub Bucket Type')
    invoice_number = fields.Many2one('account.move', 'Invoice Number')


    def fetch_vendor_paid_bills(self,fetch_bills):
        for record in fetch_bills:
            if record.partner_id.id == self.vendor_id.id:
                # if record.state == 'posted' and record.payment_state != 'not_paid':
                #     print("posted")
                #     if record.invoice_line_ids:
                #         visited_move_line_product = set()
                #         for move_line_product in record.invoice_line_ids:
                #             visited_move_line_product.add(move_line_product.product_id.id)
                #             if move_line_product.product_id:
                #                 vendor_id = self.env["product.supplierinfo"].sudo().search(
                #                     [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                #                     limit=1, order="id desc")
                #                 vendor_id = vendor_id.partner_id
                #             else:
                #                 vendor_id = self.vendor_id
                #             print(move_line_product.bucket_sub_type,"sub typeee")
                #             existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                #                 [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                #                  ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id),
                #                  ('bucket_sub_type','=',move_line_product.bucket_sub_type.id)])
                #             print(existing_bill_rec,">>>>>>>>>>>>>>>>>>>>>>>")
                #             total_amount_paid = 0
                #             for move_line_product in record.invoice_line_ids:
                #                 if move_line_product.product_id.id in visited_move_line_product:
                #                     total_amount_paid += move_line_product.price_subtotal
                #                 else:
                #                     total_amount_paid = move_line_product.price_subtotal
                #             if not existing_bill_rec:
                #                 self.env['vendor.bill.detail'].sudo().create({
                #                     'bill_name': record.id,
                #                     'vendor_id': vendor_id.id,
                #                     'vendor_amount_paid': total_amount_paid,
                #                     'vendor_amount_due': total_amount_paid,
                #                     'bill_paid': True,
                #                     'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id,
                #                     'bucket_sub_type':move_line_product.bucket_sub_type.id
                #                 })
                #             else:
                #                 existing_bill_rec.write({
                #                     'vendor_amount_bill': 0.0,
                #                     'vendor_amount_paid': total_amount_paid,
                #                     'bill_paid': True,
                #                 })

                if record.state == 'posted' and record.payment_state in ("paid", "in_payment"):
                    if record.invoice_line_ids:
                        visited_move_line_product = set()
                        for move_line_product in record.invoice_line_ids:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.product_id:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                    limit=1, order="id desc")
                                vendor_id = vendor_id.partner_id
                            else:
                                vendor_id = self.vendor_id
                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                 ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id),
                                 ('bucket_sub_type','=',move_line_product.bucket_sub_type.id)])
                            total_amount_paid = 0
                            for move_line_product in record.invoice_line_ids:
                                if move_line_product.product_id.id in visited_move_line_product:
                                    total_amount_paid += move_line_product.price_subtotal
                                else:
                                    total_amount_paid = move_line_product.price_subtotal
                            if not existing_bill_rec:
                                self.env['vendor.bill.detail'].sudo().create({
                                    'bill_name': record.id,
                                    'vendor_id': vendor_id.id,
                                    'vendor_amount_paid': total_amount_paid,
                                    'vendor_amount_due': total_amount_paid,
                                    'bill_paid': True,
                                    'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                    'bucket_sub_type': move_line_product.bucket_sub_type.id
                                })
                            else:
                                existing_bill_rec.write({
                                    'vendor_amount_bill': 0.0,
                                    'vendor_amount_paid': total_amount_paid,
                                    'vendor_amount_due': total_amount_paid,
                                    'bill_paid': True,
                                })

                if record.state == 'posted' and record.payment_state == 'partial':
                    if record.invoice_line_ids:
                        visited_move_line_product = set()
                        total_amount_paid = 0
                        remaining_bill_amount = 0
                        for move_line_product in record.invoice_line_ids:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.bill_residual_amount != 0.0:
                                if not move_line_product.is_bill_paid:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1, order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id), (
                                        'bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id),
                                         ('bucket_sub_type','=',move_line_product.bucket_sub_type.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id),('vendor_line_released_bucket_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])

                                    if move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                        remaining_bill_amount += move_line_product.price_subtotal
                                    elif move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                        remaining_bill_amount += move_line_product.bill_residual_amount
                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount == move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal
                                        remaining_bill_amount += move_line_product.price_subtotal

                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.bill_residual_amount != move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                        remaining_bill_amount += move_line_product.bill_residual_amount

                                    if not existing_bill_rec:

                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': remaining_bill_amount,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': total_amount_paid,
                                            'vendor_amount_due': total_amount_paid + remaining_bill_amount,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                            'bucket_sub_type': move_line_product.bucket_sub_type.id
                                        })
                                    else:
                                        existing_bill_rec.write({'vendor_amount_paid': total_amount_paid,
                                                                 'vendor_amount_due':total_amount_paid + remaining_bill_amount,
                                                                 'vendor_amount_bill': remaining_bill_amount,
                                                                 'bill_paid': move_line_product.is_bill_paid})
                                else:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1, order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                         ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id),
                                         ('bucket_sub_type','=',move_line_product.bucket_sub_type.id)])
                                         
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    total_amount_paid = 0
                                    if move_line_product.product_id.id in visited_move_line_product and move_line_product.is_partial:
                                        total_amount_paid += move_line_product.price_subtotal
                                    elif move_line_product.is_partial and not move_line_product.is_bill_paid:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': total_amount_paid,
                                            'vendor_amount_due': total_amount_paid,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                            'bucket_sub_type': move_line_product.bucket_sub_type.id
                                        })
                                    else:
                                        existing_bill_rec.write({'vendor_amount_paid': total_amount_paid,'bill_paid': move_line_product.is_bill_paid})
                            else:
                                if move_line_product.is_bill_paid:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1,
                                            order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                         (
                                         'bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id),
                                         ('bucket_sub_type','=',move_line_product.bucket_sub_type.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': move_line_product.price_subtotal,
                                            'vendor_amount_due': move_line_product.price_subtotal,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                            'bucket_sub_type': move_line_product.bucket_sub_type.id
                                        })
                                    else:
                                        existing_bill_rec.write({
                                                                    'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                                    'vendor_amount_bill': 0.0,
                                                                    'bill_paid': move_line_product.is_bill_paid, })
                                        
                                        

    def fetch_vendor_refunded_bills(self,fetch_refunded_bills):
        for record in fetch_refunded_bills:
            if record.partner_id.id == self.vendor_id.id:
                if record.state == 'posted' and record.payment_state in ("paid","in_payment"):
                    if record.invoice_line_ids:
                        visited_move_line_product = set()
                        for move_line_product in record.invoice_line_ids:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.product_id:
                                vendor_id = self.env["product.supplierinfo"].sudo().search([('product_tmpl_id','=',move_line_product.product_id.product_tmpl_id.id)],limit=1,order="id desc")
                                vendor_id = vendor_id.partner_id
                            else:
                                vendor_id = self.vendor_id
                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search([('bill_name','=',record.reversed_entry_id.id),('vendor_id','=',vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                            vendor_line_released_id = self.search([('vendor_id','=',vendor_id.id),('vendor_line_released_bucket_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                            total_amount_refunded = 0
                            for move_line_product in record.invoice_line_ids:
                                if move_line_product.product_id.id in visited_move_line_product:
                                    total_amount_refunded += move_line_product.price_subtotal
                                else:
                                    total_amount_refunded = move_line_product.price_subtotal

                            if not existing_bill_rec:
                                self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name':record.reversed_entry_id.id,
                                            'vendor_id':vendor_id.id,
                                            # 'vendor_amount_bill':move_line_product.price_subtotal,
                                            'vendor_line_released_id':vendor_line_released_id.id,
                                            'vendor_bill_amount_refunded':total_amount_refunded,
                                            'vendor_amount_paid':total_amount_refunded,
                                            'bill_paid':True,
                                            'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id

                                        })
                            else:
                                existing_bill_rec.write({
                                    'vendor_amount_bill':0.0,
                                    'vendor_bill_amount_refunded':total_amount_refunded,
                                    'bill_paid': True,
                                })
                if record.state == 'posted' and record.payment_state == 'partial':
                    if record.reversed_entry_id.invoice_line_ids:
                        visited_move_line_product = set()
                        total_amount_paid = 0
                        remaining_bill_amount = 0
                        total_refund = 0
                        for move_line_product in record.reversed_entry_id.invoice_line_ids:
                            visited_move_line_product.add(move_line_product.product_id.id)
                            if move_line_product.bill_residual_amount != 0.0:
                                if not move_line_product.is_bill_paid:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1, order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.reversed_entry_id.id), ('vendor_id', '=', vendor_id.id),
                                         ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])

                                    if move_line_product.product_id.id in visited_move_line_product and move_line_product.refund_residual_amount == move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                                        remaining_bill_amount += move_line_product.price_subtotal
                                    elif move_line_product.product_id.id in visited_move_line_product and move_line_product.refund_residual_amount != move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                                        remaining_bill_amount += move_line_product.refund_residual_amount
                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.refund_residual_amount == move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal
                                        remaining_bill_amount += move_line_product.price_subtotal

                                    elif not move_line_product.product_id.id in visited_move_line_product and move_line_product.refund_residual_amount != move_line_product.price_subtotal:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                                        remaining_bill_amount += move_line_product.refund_residual_amount
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': remaining_bill_amount,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': total_amount_paid,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id

                                        })
                                    else:
                                        existing_bill_rec.write({'vendor_amount_paid': total_amount_paid,
                                                                 'vendor_amount_bill': remaining_bill_amount,
                                                                 'bill_paid': move_line_product.is_bill_paid})
                                else:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1, order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                         ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    total_amount_paid = 0
                                    if move_line_product.product_id.id in visited_move_line_product and move_line_product.is_partial:
                                        total_amount_paid += move_line_product.price_subtotal
                                    elif move_line_product.is_partial and not move_line_product.is_bill_paid:
                                        total_amount_paid += move_line_product.price_subtotal - move_line_product.bill_residual_amount
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': total_amount_paid,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id

                                        })
                                    else:
                                        existing_bill_rec.write({'vendor_amount_paid': total_amount_paid,
                                                                 'bill_paid': move_line_product.is_bill_paid})
                            else:
                                if move_line_product.is_bill_refunded:
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1,
                                            order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.reversed_entry_id.id), ('vendor_id', '=', vendor_id.id),
                                         ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.reversed_entry_id.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': move_line_product.price_subtotal,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id

                                        })
                                    else:
                                        existing_bill_rec.write({
                                                                    'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                                    'vendor_amount_bill': 0.0,
                                                                    'bill_paid': move_line_product.is_bill_paid, })
                                else:
                                    total_refund += move_line_product.price_subtotal - move_line_product.refund_residual_amount
                                    if move_line_product.product_id:
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1,
                                            order="id desc")
                                        vendor_id = vendor_id.partner_id
                                    else:
                                        vendor_id = self.vendor_id
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.reversed_entry_id.id),
                                         ('vendor_id', '=', vendor_id.id),
                                         ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                                    vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.id)])
                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.reversed_entry_id.id,
                                            'vendor_id': vendor_id.id,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_released_id': vendor_line_released_id.id,
                                            'vendor_amount_paid': move_line_product.price_subtotal,
                                            'vendor_bill_amount_refunded': total_refund,
                                            'bill_paid': move_line_product.is_bill_paid,
                                            'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id,

                                        })
                                    else:
                                        existing_bill_rec.write({
                                            'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                            'vendor_amount_bill': 0.0,
                                            'vendor_bill_amount_refunded': total_refund,
                                            'bill_paid': move_line_product.is_bill_paid, })
                                        
                                        


    def fetch_ven_bill_details(self):
        fetch_bills = self.env['account.move'].sudo().search([('move_type','=',"in_invoice")])
        fetch_refunded_bills = self.env['account.move'].sudo().search([('move_type','=',"in_refund")])
        self.fetch_vendor_paid_bills(fetch_bills)
        self.fetch_vendor_refunded_bills(fetch_refunded_bills)
        domain = [('vendor_id','=',self.vendor_id.id),("debit",'=',False),('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id),('bill_name.payment_state','in',('paid','in_payment','partial'))]

        vals = {
            'name': _('Bill Detail'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'target':'new',
            'res_model': 'vendor.bill.detail',
        }
        return vals
    


    def fetch_vendor_unpaid_invoice_details_rel(self,final_invoice_no):
        for invoices in final_invoice_no:
            print(invoices,"invoicessrelease unpaid")
            refund_invoice_id = self.env["account.move"].sudo().search([('reversed_entry_id', '=', invoices.id)])
            if invoices.state == 'posted' and invoices.move_type == "out_invoice" and not refund_invoice_id:
                if invoices.payment_state == 'partial':
                    print("partllll")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_invoice_rel = 0.0
                    total_paid_amount_rel = 0.0
                    total_invoice_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id and inv_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id:
                            total_paid_amount_inv += inv_budget_line.amount_residual
                            total_amount_inv += inv_budget_line.amount
                            exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                [('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                 ('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),
                                 ('bucket_sub_type', '=', False)])

                            if not exist_invoice_number:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {'vendor_id': self.vendor_id.id, 'invoice_name': invoices.id,
                                     'bucket_type_id': inv_budget_line.bucket_type_id.id,
                                     'vendor_inv_amount': inv_budget_line.amount,
                                     'vendor_amount_invoiced': inv_budget_line.amount_residual,
                                     'vendor_amount_released': inv_budget_line.amount - inv_budget_line.amount_residual,
                                     'partial_due_amount': inv_budget_line.amount_residual,
                                     'partial_paid_amount': inv_budget_line.amount - inv_budget_line.amount_residual
                                     })
                            else:
                                if inv_budget_line.amount_residual > 0:
                                    exist_invoice_number.write({'released':False,'vendor_inv_amount': inv_budget_line.amount,'vendor_amount_invoiced': inv_budget_line.amount_residual,
                                     'vendor_amount_released': inv_budget_line.amount - inv_budget_line.amount_residual,'partial_due_amount': inv_budget_line.amount_residual,
                                     'partial_paid_amount': inv_budget_line.amount - inv_budget_line.amount_residual})
                                else:
                                    exist_invoice_number.write(
                                        {'released': True, 'vendor_inv_amount': inv_budget_line.amount,
                                         'vendor_amount_invoiced': inv_budget_line.amount_residual,
                                         'vendor_amount_released': inv_budget_line.amount - inv_budget_line.amount_residual,
                                         'partial_due_amount': inv_budget_line.amount_residual,
                                         'partial_paid_amount': inv_budget_line.amount - inv_budget_line.amount_residual})

                    all_fixed_amount_released = []
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(invoices.inv_budget_line):
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id == False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),('bucket_sub_type', '=', False)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': total_paid_invoice_rel,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    exist_invoice_number.write(
                                        {'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                            if product_remaining_budget_line.prod_remaining_id.id == self.invoice_number.id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': False, 'invoice_name': invoices.id,'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': total_paid_invoice_rel,'vendor_amount_released': product_remaining_budget_line.amount - total_paid_invoice_rel,
                                         'partial_due_amount': total_paid_invoice_rel,'partial_paid_amount': product_remaining_budget_line.amount - total_paid_invoice_rel
                                         })
                                else:
                                    if product_remaining_budget_line.amount_residual > 0:
                                        exist_invoice_number.write({'released':False,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                             'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                             'partial_due_amount': product_remaining_budget_line.amount_residual,'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})

                                    else:
                                        exist_invoice_number.write({'released':True,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                             'partial_due_amount': product_remaining_budget_line.amount_residual,'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})

                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id),('vendor_id', '=', self.vendor_id.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': self.vendor_id.id, 'invoice_name': invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual,'partial_due_amount':product_remaining_budget_line.amount_residual,
                                        'partial_paid_amount':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual
                                    })
                                else:
                                    if product_remaining_budget_line.amount_residual > 0:
                                        exist_invoice_number.write({'released':False,'vendor_inv_amount':product_remaining_budget_line.amount,'vendor_amount_invoiced':product_remaining_budget_line.amount_residual,'vendor_amount_released':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual,
                                                                'partial_due_amount':product_remaining_budget_line.amount_residual,'partial_paid_amount':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual})
                                    else:
                                        exist_invoice_number.write({'released':True,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual, 'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                             'partial_due_amount': product_remaining_budget_line.amount_residual,'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                    else:
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id == False:

                                total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                total_invoice_rel += product_remaining_budget_line.amount
                            if product_remaining_budget_line.prod_remaining_id.id == self.invoice_number.id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                    [('invoice_name', '=', invoices.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create(
                                        {'vendor_id': False, 'invoice_name': invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                         'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': total_paid_invoice_rel,
                                         'vendor_amount_released': product_remaining_budget_line.amount - total_paid_invoice_rel,
                                         'partial_due_amount': total_paid_invoice_rel,
                                         'partial_paid_amount': product_remaining_budget_line.amount - total_paid_invoice_rel
                                         })
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                    [('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])

                                if not exist_invoice_number:

                                    create_record = self.env['vendor.invoice.detail'].sudo().create(
                                        {'vendor_id': self.vendor_id.id, 'invoice_name': invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                         'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': total_paid_invoice_rel,
                                         'vendor_amount_released': product_remaining_budget_line.amount - total_paid_invoice_rel,
                                         'partial_due_amount': total_paid_invoice_rel,
                                         'partial_paid_amount': product_remaining_budget_line.amount - total_paid_invoice_rel
                                         })

                    total_vendor_paid_amount = total_amount_inv + total_invoice_rel
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_invoice_rel
                    vendor_lst_inv = []
                    vendor_lst_rel = []
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and inv_budget_line.budget_inv_vendor_id.id == self.vendor_id.id:
                            vendor_lst_inv.append(inv_budget_line.budget_inv_vendor_id.id)
                    for product_remaining_budget_line in invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.budget_inv_remaining_vendor_id.id == self.vendor_id.id and product_remaining_budget_line.sub_bucket_type.id == False:
                            vendor_lst_rel.append(product_remaining_budget_line.budget_inv_remaining_vendor_id.id)

                    if len(vendor_lst_rel) == len(vendor_lst_inv) and len(vendor_lst_inv) > 0 and len(vendor_lst_rel) > 0:
                        existing_record_1 = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', invoices.id),('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id),('bucket_sub_type','=',False)])

                        if total_vendor_amount_part_paid_per_invoice != 0.0:
                            if existing_record_1:
                                existing_record_1.write({'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                            else:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id,'vendor_inv_amount':total_vendor_paid_amount,
                                     'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})
                        else:
                            if existing_record_1:
                                existing_record_1.write({'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                            else:
                                self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id,'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                # if invoices.payment_state == 'partial':
                #     print("partial relesss")
                #     total_vendor_amount = 0.0
                #     total_amount_inv = 0.0
                #     total_amount_rel = 0.0
                #     total_paid_amount_inv = 0.0
                #     total_paid_amount_rel = 0.0
                #     for inv_budget_line in invoices.inv_budget_line:
                #         if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                #             total_paid_amount_inv += inv_budget_line.amount_residual
                #             total_amount_inv += inv_budget_line.amount
                #     all_fixed_amount_released = []
                #     for inv_budget_line in invoices.inv_budget_line:
                #         if inv_budget_line.released:
                #             all_fixed_amount_released.append(inv_budget_line.id)
                #     if len(all_fixed_amount_released) == len(invoices.inv_budget_line):
                #         for product_remaining_budget_line in invoices.product_remaining_budget_line:
                #             if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                #                 total_paid_amount_rel += product_remaining_budget_line.amount_residual
                #                 total_amount_rel += product_remaining_budget_line.amount
                #     else:
                #         for product_remaining_budget_line in invoices.product_remaining_budget_line:
                #             if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                #                 total_paid_amount_rel += product_remaining_budget_line.amount
                #                 total_amount_rel += product_remaining_budget_line.amount
                #
                #     total_vendor_paid_amount = total_amount_inv + total_amount_rel
                #     total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                #     existing_record_2 = self.env['vendor.invoice.detail'].sudo().search(
                #         [('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                #     if total_vendor_amount_part_paid_per_invoice != 0.0:
                #
                #         if existing_record_2:
                #             existing_record_2.write({'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                #         else:
                #             vals = {"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id,'vendor_inv_amount':total_vendor_paid_amount,
                #                  'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice}
                #             create_record = self.env['vendor.invoice.detail'].sudo().create(vals)
                #     else:
                #         if existing_record_2:
                #             existing_record_2.write({'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                #         else:
                #             self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id,'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})

                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('vendor_id','=',self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                    if not existing_record:
                        create_record = self.env['vendor.invoice.detail'].sudo().create({"vendor_id":self.vendor_id.id,'invoice_name':invoices.id,"bucket_type_id":self.vendor_line_released_bucket_id.bucket_type_id.id,'vendor_amount_invoiced':total_vendor_amount_per_invoice,'vendor_inv_amount':total_vendor_amount_per_invoice})

    
    
    def fetch_vendor_paid_invoice_details_rel(self,final_paid_invoice_no):
        for paid_invoices in final_paid_invoice_no:
            print("paid invoicesss")
            refunded_invoice_id = self.env["account.move"].sudo().search([('reversed_entry_id', '=', paid_invoices.id)])
            if paid_invoices.state == 'posted' and paid_invoices.move_type == 'out_invoice' and not refunded_invoice_id:
                if paid_invoices.payment_state == 'partial':
                    print("partialala")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id and inv_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id:
                            total_paid_amount_inv += inv_budget_line.amount_residual
                            total_amount_inv += inv_budget_line.amount
                            exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                 ('bucket_type_id', '=', inv_budget_line.bucket_type_id.id),('bucket_sub_type', '=', False)])

                            if not exist_invoice_number:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {'vendor_id': self.vendor_id.id, 'invoice_name': paid_invoices.id,'released': True,'bucket_type_id': inv_budget_line.bucket_type_id.id,
                                     'vendor_inv_amount': inv_budget_line.amount,'vendor_amount_invoiced': inv_budget_line.amount_residual,
                                     'vendor_amount_released': inv_budget_line.amount - inv_budget_line.amount_residual,
                                     'partial_due_amount': inv_budget_line.amount_residual,'partial_paid_amount': inv_budget_line.amount - inv_budget_line.amount_residual
                                     })
                            else:
                                exist_invoice_number.write(
                                    {'released': True,'vendor_inv_amount': inv_budget_line.amount,'vendor_amount_invoiced': inv_budget_line.amount_residual,
                                     'vendor_amount_released': inv_budget_line.amount - inv_budget_line.amount_residual,
                                     'partial_due_amount': inv_budget_line.amount_residual,'partial_paid_amount': inv_budget_line.amount - inv_budget_line.amount_residual})
                    all_fixed_amount_released = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(paid_invoices.inv_budget_line):
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id == False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),('bucket_sub_type', '=', False)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': self.vendor_id.id,'released': True, 'invoice_name': paid_invoices.id,'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    exist_invoice_number.write({'vendor_inv_amount': product_remaining_budget_line.amount,'released': True,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'released': True,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                            if product_remaining_budget_line.prod_remaining_id.id == self.invoice_number.id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', paid_invoices.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': False, 'released': True,'invoice_name': paid_invoices.id,'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                                else:
                                    exist_invoice_number.write({'released': True,'vendor_inv_amount':product_remaining_budget_line.amount,'vendor_amount_invoiced':product_remaining_budget_line.amount_residual,'vendor_amount_released':product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                                            'partial_due_amount':product_remaining_budget_line.amount_residual,'partial_paid_amount':product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual})
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', paid_invoices.id),('vendor_id', '=', self.vendor_id.id),('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create({'vendor_id': self.vendor_id.id,'released': True, 'invoice_name': paid_invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,'vendor_inv_amount': product_remaining_budget_line.amount,'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual,'partial_due_amount':product_remaining_budget_line.amount_residual,
                                        'partial_paid_amount':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual
                                    })
                                else:
                                    exist_invoice_number.write({'released': True,'vendor_inv_amount':product_remaining_budget_line.amount,'vendor_amount_invoiced':product_remaining_budget_line.amount_residual,'vendor_amount_released':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual,
                                                                'partial_due_amount':product_remaining_budget_line.amount_residual,'partial_paid_amount':product_remaining_budget_line.amount-product_remaining_budget_line.amount_residual})
                    else:
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id == False:
                                print("ss2")
                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                            if product_remaining_budget_line.prod_remaining_id.id == self.invoice_number.id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:
                                print("cc2")
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                    [('invoice_name', '=', paid_invoices.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])
                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create(
                                        {'vendor_id': False, 'released': True,'invoice_name': paid_invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                         'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.sub_bucket_type.id != False:

                                # total_paid_invoice_rel += product_remaining_budget_line.amount_residual
                                # total_invoice_rel += product_remaining_budget_line.amount
                                exist_invoice_number = self.env['vendor.invoice.detail'].sudo().search(
                                    [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                     ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                     ('bucket_sub_type', '=', product_remaining_budget_line.sub_bucket_type.id)])

                                if not exist_invoice_number:
                                    create_record = self.env['vendor.invoice.detail'].sudo().create(
                                        {'vendor_id': self.vendor_id.id,'released': True, 'invoice_name': paid_invoices.id,
                                         'bucket_type_id': product_remaining_budget_line.bucket_type_id.id,
                                         'bucket_sub_type': product_remaining_budget_line.sub_bucket_type.id,
                                         'vendor_inv_amount': product_remaining_budget_line.amount,
                                         'vendor_amount_invoiced': product_remaining_budget_line.amount_residual,
                                         'vendor_amount_released': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual,
                                         'partial_due_amount': product_remaining_budget_line.amount_residual,
                                         'partial_paid_amount': product_remaining_budget_line.amount - product_remaining_budget_line.amount_residual
                                         })

                    total_vendor_paid_amount = total_amount_inv
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv
                    vendor_lst_inv = []
                    vendor_lst_rel = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and inv_budget_line.budget_inv_vendor_id.id == self.vendor_id.id:
                            vendor_lst_inv.append(inv_budget_line.budget_inv_vendor_id.id)
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.bucket_type_id.id == self.vendor_line_released_bucket_id.bucket_type_id.id and product_remaining_budget_line.budget_inv_remaining_vendor_id.id == self.vendor_id.id and product_remaining_budget_line.sub_bucket_type.id == False:
                            vendor_lst_rel.append(product_remaining_budget_line.budget_inv_remaining_vendor_id.id)

                    if len(vendor_lst_rel) == len(vendor_lst_inv) and len(vendor_lst_inv) > 0 and len(vendor_lst_rel) > 0:
                        existing_record_1 = self.env['vendor.invoice.detail'].sudo().search([('invoice_name', '=', paid_invoices.id),('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id),('bucket_sub_type','=',False)])

                        if total_vendor_amount_part_paid_per_invoice != 0.0:
                            if existing_record_1:
                                existing_record_1.write({'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                            else:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id,'vendor_inv_amount':total_vendor_paid_amount,
                                     'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})
                        else:
                            if existing_record_1:
                                existing_record_1.write({'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})
                            else:
                                self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id,'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount})

                # if paid_invoices.payment_state == 'partial':
                #     print("partial enter")
                #     total_vendor_amount = 0.0
                #     total_amount_inv = 0.0
                #     total_amount_rel = 0.0
                #     total_paid_amount_inv = 0.0
                #     total_paid_amount_rel = 0.0
                #     for inv_budget_line in paid_invoices.inv_budget_line:
                #         if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                #             total_paid_amount_inv += inv_budget_line.amount_residual
                #             total_amount_inv += inv_budget_line.amount
                #     all_fixed_amount_released_paid = []
                #     for inv_budget_line in paid_invoices.inv_budget_line:
                #         if inv_budget_line.released:
                #             all_fixed_amount_released_paid.append(inv_budget_line.id)
                #     if len(all_fixed_amount_released_paid) == len(paid_invoices.inv_budget_line):
                #         for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                #             if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.sub_bucket_type.id == False:
                #                 total_paid_amount_rel += product_remaining_budget_line.amount_residual
                #                 total_amount_rel += product_remaining_budget_line.amount
                #     else:
                #         for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                #             if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and product_remaining_budget_line.sub_bucket_type.id == False:
                #                 total_paid_amount_rel += product_remaining_budget_line.amount
                #                 total_amount_rel += product_remaining_budget_line.amount
                #     total_vendor_paid_amount = total_amount_inv + total_amount_rel
                #     total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                #     existing_record_1 = self.env['vendor.invoice.detail'].sudo().search(
                #         [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                #          ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                #     print(existing_record_1,"existing record 1")
                #     if total_vendor_amount_part_paid_per_invoice != 0.0:
                #         if existing_record_1:
                #             existing_record_1.write(
                #                 {'vendor_amount_invoiced': total_vendor_amount_part_paid_per_invoice,
                #                  'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                #                  'partial_due_amount': total_vendor_amount_part_paid_per_invoice,
                #                  'partial_paid_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                #                  'vendor_inv_amount':total_vendor_paid_amount})
                #         else:
                #             create_record = self.env['vendor.invoice.detail'].sudo().create(
                #                 {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                #                  'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id,
                #                  'vendor_amount_invoiced': total_vendor_amount_part_paid_per_invoice,
                #                  'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                #                  'partial_due_amount': total_vendor_amount_part_paid_per_invoice,
                #                  'partial_paid_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                #                  'vendor_inv_amount':total_vendor_paid_amount})
                #
                #     else:
                #         if existing_record_1:
                #             existing_record_1.write(
                #                 {'released': True, 'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                #                  'partial_paid_amount': 0.0,
                #                  'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                #                  'vendor_inv_amount':total_vendor_paid_amount})
                #         else:
                #             self.env['vendor.invoice.detail'].sudo().create(
                #                 {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                #                  'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id,
                #                  'released': True,
                #                  'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                #                  'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                #                  'vendor_inv_amount':total_vendor_paid_amount})
                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            existing_vendor_line = self.env['vendor.invoice.detail'].sudo().search(
                                [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                 ('bucket_type_id', '=', inv_budget_line.bucket_type_id.id)])
                            if not existing_vendor_line:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                                     "bucket_type_id": inv_budget_line.bucket_type_id.id,
                                     'released': True, 'vendor_amount_released': inv_budget_line.amount,
                                     'vendor_inv_amount': inv_budget_line.amount,
                                     'vendor_amount_invoiced': 0.0})
                            else:
                                existing_vendor_line.write(
                                    {'vendor_amount_released': inv_budget_line.amount, 'released': True,
                                     'vendor_amount_invoiced': 0.0,
                                     'vendor_inv_amount': inv_budget_line.amount, })
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.sub_bucket_type.id != False:
                            total_amount_rel += product_remaining_budget_line.amount
                            existing_sub_line = self.env['vendor.invoice.detail'].sudo().search(
                                [('invoice_name', '=', paid_invoices.id),
                                 ('bucket_type_id', '=', product_remaining_budget_line.bucket_type_id.id),
                                 ('bucket_sub_type','=',product_remaining_budget_line.sub_bucket_type.id)])

                            if not existing_sub_line:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {'invoice_name': paid_invoices.id,
                                     "bucket_type_id": product_remaining_budget_line.bucket_type_id.id,
                                     'bucket_sub_type':product_remaining_budget_line.sub_bucket_type.id,
                                     'released': True, 'vendor_amount_released': product_remaining_budget_line.amount,
                                     'vendor_inv_amount': product_remaining_budget_line.amount,
                                     'vendor_amount_invoiced': 0.0})
                            else:
                                existing_sub_line.write(
                                        {'vendor_amount_released': product_remaining_budget_line.amount, 'released': True,
                                         'vendor_amount_invoiced': 0.0,'vendor_inv_amount':product_remaining_budget_line.amount,})

                        if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id and not product_remaining_budget_line.sub_bucket_type.id:
                            existing_vendor_line = self.env['vendor.invoice.detail'].sudo().search(
                                [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                                 ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                            if not existing_vendor_line:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                                     "bucket_type_id": self.vendor_line_released_bucket_id.bucket_type_id.id,
                                     'released': True, 'vendor_amount_released': product_remaining_budget_line.amount,
                                     'vendor_inv_amount': product_remaining_budget_line.amount,
                                     'vendor_amount_invoiced': 0.0})
                            else:
                                existing_vendor_line.write(
                                        {'vendor_amount_released': product_remaining_budget_line.amount, 'released': True,
                                         'vendor_amount_invoiced': 0.0,'vendor_inv_amount':product_remaining_budget_line.amount,})
                    # total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    # print(paid_invoices.id,"paid id")
                    # existing_record = self.env['vendor.invoice.detail'].sudo().search(
                    #     [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                    #      ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                    # print(existing_record,"record dexitt")
                    # if not existing_record:
                    #     create_record = self.env['vendor.invoice.detail'].sudo().create(
                    #         {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                    #          "bucket_type_id": self.vendor_line_released_bucket_id.bucket_type_id.id,
                    #          'released': True, 'vendor_amount_released': total_vendor_amount_per_invoice,
                    #          'vendor_inv_amount':total_vendor_amount_per_invoice,
                    #          'vendor_amount_invoiced': 0.0})
                    #     print(create_record,"recodd dreeee")
                    # else:
                    #     existing_record.write(
                    #         {'vendor_amount_released': total_vendor_amount_per_invoice, 'released': True,
                    #          'vendor_amount_invoiced': 0.0,'vendor_inv_amount':total_vendor_amount_per_invoice,})
            if paid_invoices.state == 'posted' and paid_invoices.move_type == 'out_refund':
                if paid_invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    vendor_id_check = False
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            vendor_id_check = True
                            total_paid_amount_inv += inv_budget_line.refund_residual
                            total_amount_inv += inv_budget_line.amount
                    all_fixed_amount_released_paid = []
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        if inv_budget_line.item_refunded:
                            all_fixed_amount_released_paid.append(inv_budget_line.item_refunded)
                    if len(all_fixed_amount_released_paid) == len(paid_invoices.reversed_entry_id.inv_budget_line):
                        for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                vendor_id_check = True
                                total_paid_amount_rel += product_remaining_budget_line.refund_residual
                                total_amount_rel += product_remaining_budget_line.amount
                    else:
                        for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                vendor_id_check = True
                                total_paid_amount_rel += product_remaining_budget_line.amount
                                total_amount_rel += product_remaining_budget_line.amount
                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel

                    existing_record_1 = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.reversed_entry_id.id),
                         ('vendor_id', '=', self.vendor_id.id),
                         ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])

                    if total_vendor_amount_part_paid_per_invoice != 0.0:
                        if existing_record_1 and vendor_id_check:
                            existing_record_1.write(
                                {'released': True, 'refunded_invoice_name': paid_invoices.id,
                                 'refunded_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                 'vendor_amount_released': total_vendor_amount_part_paid_per_invoice,'vendor_inv_amount':total_vendor_paid_amount
                                 })
                        else:
                            if vendor_id_check:
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,
                                     'refunded_invoice_name': paid_invoices.id,
                                     'released': True,
                                     'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id,
                                     'vendor_amount_released': total_vendor_amount_part_paid_per_invoice,
                                     'refunded_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                     'vendor_inv_amount': total_vendor_paid_amount
                                     })

                    else:
                        if existing_record_1 and vendor_id_check:
                            existing_record_1.vendor_amount_released = 0.0
                            existing_record_1.write(
                                {'released': True, 'refunded_invoice_name': paid_invoices.id,
                                 'refunded_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                 'vendor_inv_amount':total_vendor_paid_amount
                                 })
                        else:
                            if vendor_id_check:
                                self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,
                                     'refunded_invoice_name': paid_invoices.id,
                                     'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id,
                                     'released': True,
                                     'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                     'partial_paid_amount': 0.0,
                                     'vendor_amount_released': 0.0,
                                     'refunded_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                     'vendor_inv_amount': total_vendor_paid_amount
                                     })

                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    vendor_id_check = False
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            vendor_id_check = True
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                        if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                            vendor_id_check = True
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv

                    existing_record = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.reversed_entry_id.id),
                         ('vendor_id', '=', self.vendor_id.id),
                         ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                    if not existing_record and vendor_id_check:
                        create_record = self.env['vendor.invoice.detail'].sudo().create(
                            {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,
                             'refunded_invoice_name': paid_invoices.id,
                             "bucket_type_id": self.vendor_line_released_bucket_id.bucket_type_id.id,
                             'released': True, 'vendor_amount_released': 0.0,
                             'vendor_amount_invoiced': 0.0, 'refunded_amount': total_vendor_amount_per_invoice,
                             'vendor_inv_amount':total_vendor_amount_per_invoice})
                    else:
                        if vendor_id_check:
                            existing_record.write(
                                {'vendor_amount_released': 0.0, 'released': True,
                                 'refunded_invoice_name': paid_invoices.id,
                                 'vendor_amount_invoiced': 0.0, 'refunded_amount': total_vendor_amount_per_invoice,
                                 'vendor_inv_amount':total_vendor_amount_per_invoice})
                            
                            

    def fetch_vendor_invoice_details_rel(self):
        print("release invoice details")

        all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_inv_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
        all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_inv_remaining_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
        all_invoice_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('prod_remaining_id.id', '=', self.invoice_number.id), ('released', '=', False),
             ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])

        all_invoices = []
        for invoice_line in all_vendor_invoice_lines:
            all_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_vendor_remaining_lines:
            all_invoices.append(remaining_inv_line.prod_remaining_id)
        for remaining_invoice in all_invoice_remaining_lines:
            all_invoices.append(remaining_invoice.prod_remaining_id)
        rem_duplicate_invoice_no_set = set(all_invoices)
        final_invoice_no = list(rem_duplicate_invoice_no_set)
        print(final_invoice_no,"final invoice no")
        self.fetch_vendor_unpaid_invoice_details_rel(final_invoice_no)

        all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_inv_vendor_id.id', '=', self.vendor_id.id), ('released', '=', True),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
        all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_inv_remaining_vendor_id.id', '=', self.vendor_id.id), ('released', '=', True),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
        all_inovice_remaining_lines_paid = self.env['product.budget.remaining'].sudo().search(
            [('prod_remaining_id', '=', self.invoice_number.id), ('released', '=', True),('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id),('assignable_status', '=', 'unassigned')])

        print(all_inovice_remaining_lines_paid)
        print(self.invoice_number.id)
        print(self.vendor_line_released_bucket_id.bucket_type_id.id)

        all_paid_invoices = []

        for invoice_line in all_vendor_invoice_lines:
            all_paid_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_vendor_remaining_lines:
            all_paid_invoices.append(remaining_inv_line.prod_remaining_id)
        for remaining_invoice_line in all_inovice_remaining_lines_paid:
            all_paid_invoices.append(remaining_invoice_line.prod_remaining_id)
        refunded_invoices = self.env["account.move"].sudo().search([('reversed_entry_id', '!=', False)])
        for refunded_invoice in refunded_invoices:
            all_paid_invoices.append(refunded_invoice)
        rem_duplicate_paid_invoice_no_set = set(all_paid_invoices)
        final_paid_invoice_no = list(rem_duplicate_paid_invoice_no_set)
        print(final_paid_invoice_no,"final paidd inv")
        self.fetch_vendor_paid_invoice_details_rel(final_paid_invoice_no)

        domain = ['|',('released','=',True),('partial_due_amount','>',0.0),('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id),
                  ('vendor_amount_released','>=',0.0),('invoice_name.payment_state','in',('paid','in_payment','partial'))]
        if not self.invoice_number:
            vals = {
                'name': _('Details'),
                'domain': ['|',('released','=',True),('partial_due_amount','>',0.0),('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id),
                      ('vendor_amount_released','>=',0.0),('invoice_name.payment_state','in',('paid','in_payment','partial'))],
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'target':'new',
                'res_model': 'vendor.invoice.detail',
            }
        else:

            vals = {
                'name': _('Details'),
                'domain': ['|', ('released', '=', True), ('partial_due_amount', '>', 0.0),

                           ('invoice_name','=',self.invoice_number.id),
                           ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id),
                           ('vendor_amount_released', '>=', 0.0),
                           ('invoice_name.payment_state', 'in', ('paid', 'in_payment', 'partial'))],
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'target': 'new',
                'res_model': 'vendor.invoice.detail',
            }
        return vals



class UserLine(models.Model):
    _name = "user.line"


    user_id = fields.Many2one('res.partner', 'Name')
    user_line_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount_released = fields.Float('Inv. Released')
    total_amount_invoiced = fields.Float('Amount')
    total_amount_billed = fields.Float('Bill Released')
    total_amount_billed_due = fields.Float('Bill Due')



    def fetch_user_unpaid_invoice_details(self,final_invoice_no):
        for invoices in final_invoice_no:
            if invoices.state == 'posted':
                if invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                            total_paid_amount_inv += inv_budget_line.amount_residual

                    all_fixed_amount_released = []
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(invoices.inv_budget_line):

                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    else:
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount

                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', invoices.id), ('user_id', '=', self.user_id.id),('bucket_type_id','=',self.user_line_bucket_id.bucket_type_id.id)])
                    if total_user_amount_part_paid_per_invoice != 0.0:
                        if existing_record_1:
                            existing_record_1.write(
                                {'user_amount_invoiced': total_user_amount_part_paid_per_invoice,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_user_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            create_record = self.env['user.invoice.detail'].sudo().create(
                                {"user_id": self.user_id.id, 'invoice_name': invoices.id,
                                 'bucket_type_id': self.user_line_bucket_id.bucket_type_id.id,
                                 'user_amount_invoiced': total_user_amount_part_paid_per_invoice,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_user_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})

                    else:
                        if existing_record_1:
                            existing_record_1.write(
                                {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            self.env['user.invoice.detail'].sudo().create(
                                {"user_id": self.user_id.id, 'invoice_name': invoices.id,
                                 'bucket_type_id': self.user_line_bucket_id.bucket_type_id.id, 'released': True,
                                 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('user_id','=',self.user_id.id),('bucket_type_id','=',self.user_line_bucket_id.bucket_type_id.id)])
                    if not existing_record:
                        create_record = self.env['user.invoice.detail'].sudo().create({"user_id":self.user_id.id,"bucket_type_id":self.user_line_bucket_id.bucket_type_id.id,'invoice_name':invoices.id,'user_amount_invoiced':total_vendor_amount_per_invoice})


    
    
    def fetch_user_paid_invoice_details(self,final_paid_invoice_no):
        for paid_invoices in final_paid_invoice_no:
            if paid_invoices.state == 'posted':
                if paid_invoices.payment_state == 'partial':

                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                            total_paid_amount_inv += inv_budget_line.amount_residual

                    all_fixed_amount_released_paid = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released_paid.append(inv_budget_line.id)
                    if len(all_fixed_amount_released_paid) == len(paid_invoices.inv_budget_line):

                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    else:
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount
                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_bucket_id.bucket_type_id.id)])
                    if total_user_amount_part_paid_per_invoice != 0.0:
                        if existing_record_1:
                            existing_record_1.write(
                                {'user_amount_invoiced': total_user_amount_part_paid_per_invoice,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_user_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            create_record = self.env['user.invoice.detail'].sudo().create(
                                {"user_id": self.user_id.id, 'invoice_name': paid_invoices.id,
                                 'bucket_type_id': self.user_line_bucket_id.bucket_type_id.id,
                                 'user_amount_invoiced': total_user_amount_part_paid_per_invoice,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_user_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})

                    else:
                        if existing_record_1:
                            existing_record_1.write(
                                {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            self.env['user.invoice.detail'].sudo().create(
                                {"user_id": self.user_id.id, 'invoice_name': paid_invoices.id,
                                 'bucket_type_id': self.user_line_bucket_id.bucket_type_id.id, 'released': True,
                                 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})

                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_bucket_id.bucket_type_id.id)])
                    if not existing_record:
                        create_record = self.env['user.invoice.detail'].sudo().create({"user_id": self.user_id.id,
                                                                                       "bucket_type_id": self.user_line_bucket_id.bucket_type_id.id,
                                                                                       'invoice_name': paid_invoices.id,
                                                                                       'released': True,
                                                                                       'user_amount_released': total_vendor_amount_per_invoice,
                                                                                       'user_amount_invoiced': 0.0,
                                                                                       })
                    else:
                        existing_record.write({'released': True,
                                               'user_amount_released': total_vendor_amount_per_invoice,
                                               'user_amount_invoiced': 0.0,
                                               'partial_due_amount': 0.0,
                                               'partial_paid_amount': 0.0,
                                               })


    
    
    def fetch_user_invoice_details(self):
        all_user_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_user_id.id', '=', self.user_id.id), ('released', '=', False)])
        all_user_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_remaining_user_id.id', '=', self.user_id.id), ('released', '=', False)])

        all_invoices = []
        for invoice_line in all_user_invoice_lines:
            all_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_user_remaining_lines:
            all_invoices.append(remaining_inv_line.prod_remaining_id)

        rem_duplicate_invoice_no_set = set(all_invoices)
        final_invoice_no = list(rem_duplicate_invoice_no_set)
        self.fetch_user_unpaid_invoice_details(final_invoice_no)

        all_user_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_user_id.id', '=', self.user_id.id), ('released', '=', True)])
        all_user_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_remaining_user_id.id', '=', self.user_id.id), ('released', '=', True)])

        all_paid_invoices = []

        for invoice_line in all_user_invoice_lines:
            all_paid_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_user_remaining_lines:
            all_paid_invoices.append(remaining_inv_line.prod_remaining_id)

        rem_duplicate_paid_invoice_no_set = set(all_paid_invoices)
        final_paid_invoice_no = list(rem_duplicate_paid_invoice_no_set)
        self.fetch_user_paid_invoice_details(final_paid_invoice_no)
        return {
                'name': _('Details'),
                'domain': [('user_id', '=', self.user_id.id),('released','=',False),('bucket_type_id','=',self.user_line_bucket_id.bucket_type_id.id),('user_amount_invoiced','>',0.0)],
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'target': 'new',
                'res_model': 'user.invoice.detail',
            }



class UserLineReleased(models.Model):
    _name = "user.line.released"

    user_id = fields.Many2one('res.users', 'Users')
    user_line_released_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount_refunded = fields.Float('Refunded')
    total_amount_released = fields.Float('Inv. Released')
    total_amount_invoiced = fields.Float('Amount')
    total_amount_billed = fields.Float('Bill Released')
    total_amount_billed_due = fields.Float('Bill Due')

    def fetch_user_unpaid_invoice_details_rel(self,final_invoice_no):
        for invoices in final_invoice_no:
            refund_invoice_id = self.env["account.move"].sudo().search([('reversed_entry_id', '=', invoices.id)])
            if invoices.state == 'posted' and not refund_invoice_id:
                user_id_check = False
                if invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_inv += inv_budget_line.amount
                            total_paid_amount_inv += inv_budget_line.amount_residual
                    all_fixed_amount_released = []
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(invoices.inv_budget_line):
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                user_id_check = True
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    else:
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                user_id_check = True
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount

                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', invoices.id), ('user_id', '=', self.user_id.id),('bucket_type_id','=',self.user_line_released_bucket_id.bucket_type_id.id)])
                    if total_user_amount_part_paid_per_invoice != 0.0:
                        if existing_record_1 and user_id_check:
                            existing_record_1.write(
                                {'user_amount_invoiced': total_user_amount_part_paid_per_invoice,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_user_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            if user_id_check:
                                create_record = self.env['user.invoice.detail'].sudo().create(
                                    {"user_id": self.user_id.id, 'invoice_name': invoices.id,
                                     'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id,
                                     'user_amount_invoiced': total_user_amount_part_paid_per_invoice,
                                     'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                     'partial_due_amount': total_user_amount_part_paid_per_invoice,
                                     'partial_paid_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})

                    else:
                        if existing_record_1 and user_id_check:
                            existing_record_1.write(
                                {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            if user_id_check:
                                self.env['user.invoice.detail'].sudo().create(
                                    {"user_id": self.user_id.id, 'invoice_name': invoices.id,
                                     'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id, 'released': True,
                                     'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                                     'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})



                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('user_id','=',self.user_id.id),('bucket_type_id','=',self.user_line_released_bucket_id.bucket_type_id.id)])
                    if not existing_record and user_id_check:

                        create_record = self.env['user.invoice.detail'].sudo().create({"user_id":self.user_id.id,"bucket_type_id":self.user_line_released_bucket_id.bucket_type_id.id,'invoice_name':invoices.id,'user_amount_invoiced':total_vendor_amount_per_invoice})


    
    def fetch_user_paid_invoice_details_rel(self,final_paid_invoice_no):
        for paid_invoices in final_paid_invoice_no:
            refunded_invoice_id = self.env["account.move"].sudo().search([('reversed_entry_id', '=', paid_invoices.id)])
            if paid_invoices.state == 'posted' and paid_invoices.move_type == 'out_invoice' and not refunded_invoice_id:
                user_id_check = False
                if paid_invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_inv += inv_budget_line.amount
                            total_paid_amount_inv += inv_budget_line.amount_residual
                    all_fixed_amount_released_paid = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released_paid.append(inv_budget_line.id)
                    if len(all_fixed_amount_released_paid) == len(paid_invoices.inv_budget_line):
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                user_id_check = True
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    else:
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                user_id_check = True
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount

                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_released_bucket_id.bucket_type_id.id)])
                    if total_user_amount_part_paid_per_invoice != 0.0:
                        if user_id_check:
                            if existing_record_1:
                                existing_record_1.write(
                                    {'user_amount_invoiced': total_user_amount_part_paid_per_invoice,
                                     'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                     'partial_due_amount': total_user_amount_part_paid_per_invoice,
                                     'partial_paid_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                            else:
                                create_record = self.env['user.invoice.detail'].sudo().create(
                                    {"user_id": self.user_id.id, 'invoice_name': paid_invoices.id,
                                     'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id,
                                     'user_amount_invoiced': total_user_amount_part_paid_per_invoice,
                                     'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                     'partial_due_amount': total_user_amount_part_paid_per_invoice,
                                     'partial_paid_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})

                    else:
                        if user_id_check:
                            if existing_record_1 :
                                existing_record_1.write(
                                    {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                     'partial_paid_amount': 0.0,
                                     'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                            else:
                                self.env['user.invoice.detail'].sudo().create(
                                    {"user_id": self.user_id.id, 'invoice_name': paid_invoices.id,
                                     'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id, 'released': True,
                                     'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                                     'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})

                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_released_bucket_id.bucket_type_id.id)])
                    if not existing_record and user_id_check:
                        create_record = self.env['user.invoice.detail'].sudo().create({"user_id": self.user_id.id,
                                                                                       "bucket_type_id": self.user_line_released_bucket_id.bucket_type_id.id,
                                                                                       'invoice_name': paid_invoices.id,
                                                                                       'released':True,
                                                                                       'user_amount_released': total_vendor_amount_per_invoice,
                                                                                       'user_amount_invoiced': 0.0,
                                                                                       })

                    else:
                        if user_id_check:
                            existing_record.write(
                                {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0,
                                 'user_amount_released': total_vendor_amount_per_invoice})
            if paid_invoices.state == 'posted' and paid_invoices.move_type == 'out_refund':
                user_id_check = False
                if paid_invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    total_paid_amount_rel = 0.0
                    all_allocate_amount_released_paid = []
                    for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                        if product_remaining_budget_line.item_refunded:
                            all_allocate_amount_released_paid.append(product_remaining_budget_line.id)
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        if len(all_allocate_amount_released_paid) == len(
                                paid_invoices.reversed_entry_id.product_remaining_budget_line):
                            if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id and inv_budget_line.item_refunded:
                                user_id_check = True
                                total_amount_inv += inv_budget_line.amount
                                total_paid_amount_inv += inv_budget_line.refund_residual

                    for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_rel += product_remaining_budget_line.amount
                            total_paid_amount_rel += product_remaining_budget_line.refund_residual


                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.reversed_entry_id.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_released_bucket_id.bucket_type_id.id)])

                    if total_user_amount_part_paid_per_invoice != 0.0:
                        if existing_record_1 and user_id_check:
                            existing_record_1.write(
                                {'released': True,'invoice_name': paid_invoices.reversed_entry_id.id,
                                 'user_amount_released': total_user_amount_part_paid_per_invoice,
                                 'refunded_invoice_name': paid_invoices.id,
                                 'refunded_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            if user_id_check:
                                create_record = self.env['user.invoice.detail'].sudo().create(
                                    {"user_id": self.user_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,
                                     'refunded_invoice_name': paid_invoices.id,
                                     'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id,
                                     'released': True,
                                     'user_amount_released': total_user_amount_part_paid_per_invoice,
                                     'refunded_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})

                    else:
                        if existing_record_1 and user_id_check:
                            existing_record_1.write(
                                {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0, 'user_amount_released': 0.0,
                                 'refunded_invoice_name': paid_invoices.id,
                                 'refunded_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            if user_id_check:
                                self.env['user.invoice.detail'].sudo().create(
                                    {"user_id": self.user_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,
                                     'refunded_invoice_name': paid_invoices.id,
                                     'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id,
                                     'released': True,
                                     'partial_due_amount': 0.0,
                                     'refunded_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                     'user_amount_released': 0.0})

                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.reversed_entry_id.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_released_bucket_id.bucket_type_id.id)])

                    if not existing_record and user_id_check:
                        self.env['user.invoice.detail'].sudo().create({"user_id": self.user_id.id,
                                                                                       "bucket_type_id": self.user_line_released_bucket_id.bucket_type_id.id,
                                                                                       'invoice_name': paid_invoices.reversed_entry_id.id,
                                                                                       'refunded_invoice_name': paid_invoices.id,
                                                                                       'released': True,
                                                                                       'user_amount_released': 0.0,
                                                                                       'user_amount_invoiced': 0.0,
                                                                                       'refunded_amount': total_vendor_amount_per_invoice,
                                                                                       })

                    else:
                        if user_id_check:
                            existing_record.write(
                                {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0, 'refunded_invoice_name': paid_invoices.id,
                                 'user_amount_released': 0.0, 'refunded_amount': total_vendor_amount_per_invoice, })


    
    
    def fetch_user_invoice_details_rel(self):
        all_user_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_user_id.id', '=', self.user_id.id), ('released', '=', False)])
        all_user_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_remaining_user_id.id', '=', self.user_id.id), ('released', '=', False)])

        all_invoices = []
        for invoice_line in all_user_invoice_lines:
            all_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_user_remaining_lines:
            all_invoices.append(remaining_inv_line.prod_remaining_id)

        rem_duplicate_invoice_no_set = set(all_invoices)
        final_invoice_no = list(rem_duplicate_invoice_no_set)
        self.fetch_user_unpaid_invoice_details_rel(final_invoice_no)


        all_user_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_user_id.id', '=', self.user_id.id), ('released', '=', True)])
        all_user_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_remaining_user_id.id', '=', self.user_id.id), ('released', '=', True)])

        all_paid_invoices = []

        for invoice_line in all_user_invoice_lines:
            all_paid_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_user_remaining_lines:
            all_paid_invoices.append(remaining_inv_line.prod_remaining_id)
        refunded_invoices = self.env["account.move"].sudo().search([('reversed_entry_id', '!=', False)])
        for refunded_invoice in refunded_invoices:
            all_paid_invoices.append(refunded_invoice)
        rem_duplicate_paid_invoice_no_set = set(all_paid_invoices)
        final_paid_invoice_no = list(rem_duplicate_paid_invoice_no_set)
        self.fetch_user_paid_invoice_details_rel(final_paid_invoice_no)
        domain = ['|', ('released', '=', True), ('partial_due_amount', '>', 0.0),
                  ('user_id', '=', self.user_id.id), ('user_amount_released', '>=', 0.0),
                  ('bucket_type_id', '=', self.user_line_released_bucket_id.bucket_type_id.id)]

        return {
            'name': _('Details'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'user.invoice.detail',
        }
        


class VendorLineReleasedByUser(models.Model):
    _name = "vendor.line.released.inside.user"

    vendor_id = fields.Many2one('res.partner', 'Vendors')
    vendor_line_released_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount_released = fields.Float('Inv. Released')
    total_amount_refunded = fields.Float('Refunded')
    total_amount_invoiced = fields.Float('Amount')
    total_amount_billed = fields.Float('Bill Released')
    total_amount_billed_due = fields.Float('Bill Due')
    final_amount = fields.Float("Final Amount")

    def fetch_vendor_bills(self,fetch_bills):
        for record in fetch_bills:
            if self.vendor_id.id == record.partner_id.id:
                if record.state == 'posted' and record.payment_state in ("paid", "in_payment"):
                    if record.invoice_line_ids:
                        amount_paid = 0
                        for move_line_product in record.invoice_line_ids:
                            if self.vendor_line_released_bucket_id.id == move_line_product.bucket_ids.id:
                                if move_line_product.product_id:
                                    vendor_id = self.env["product.supplierinfo"].sudo().search(
                                        [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                        order="id desc")
                                    vendor_id =vendor_id.partner_id
                                else:
                                    vendor_id = self.vendor_id
                                existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                    [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                     ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                if not existing_bill_rec:
                                    self.env['vendor.bill.detail'].sudo().create({
                                        'bill_name': record.id,
                                        'vendor_id': vendor_id.id,
                                        # 'vendor_amount_bill':move_line_product.price_subtotal,
                                        'vendor_line_released_from_user_bucket_id': self.id,
                                        'vendor_amount_paid': move_line_product.price_subtotal,
                                        'bill_paid': True,
                                        'debit':True,
                                        'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id
                                    })
                                else:
                                    existing_bill_rec.write({
                                        'bill_name': record.id,
                                        'vendor_id': vendor_id.id,
                                        'vendor_amount_bill': 0.0,
                                        'vendor_amount_paid': move_line_product.price_subtotal,
                                        'bill_paid': True,
                                        'debit': True,
                                        'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id
                                    })

                if record.state == 'posted' and record.payment_state == 'partial':
                    if record.invoice_line_ids:
                        amount_paid = 0
                        amount_bill = 0
                        for move_line_product in record.invoice_line_ids:
                            if move_line_product.bill_residual_amount != 0.0:
                                if move_line_product.product_id:
                                    vendor_id = self.env["product.supplierinfo"].sudo().search(
                                        [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                        order="id desc")
                                    vendor_id = vendor_id.partner_id
                                else:
                                    vendor_id = self.vendor_id
                                existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                    [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                     ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                if not existing_bill_rec:
                                    self.env['vendor.bill.detail'].sudo().create({
                                        'bill_name': record.id,
                                        'vendor_id': vendor_id.id,
                                        'vendor_amount_bill': move_line_product.bill_residual_amount,
                                        'vendor_line_released_from_user_bucket_id': self.id,
                                        'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                        'bill_paid': move_line_product.is_bill_paid,
                                        'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id
                                    })
                                else:
                                    existing_bill_rec.write({'vendor_amount_bill': move_line_product.bill_residual_amount,
                                                                'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                                'bill_paid': move_line_product.is_bill_paid,
                                                             'bill_name': record.id,
                                                             'vendor_id': vendor_id.id,
                                                             'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id

                                                             })
                            else:
                                if move_line_product.product_id:
                                    vendor_id = self.env["product.supplierinfo"].sudo().search(
                                        [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                        order="id desc")
                                    vendor_id = vendor_id.partner_id
                                else:
                                    vendor_id = self.vendor_id
                                existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                    [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.id),
                                     ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])

                                if not existing_bill_rec:

                                    self.env['vendor.bill.detail'].sudo().create({
                                        'bill_name': record.id,
                                        'vendor_id': vendor_id.id,
                                        'vendor_amount_bill': 0.0,
                                        'vendor_line_released_from_user_bucket_id': self.id,
                                        'vendor_amount_paid': move_line_product.price_subtotal,
                                        'bill_paid': move_line_product.is_bill_paid,
                                        'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id
                                    })
                                else:

                                    existing_bill_rec.write({   'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                                                'bill_name': record.id,
                                                                'vendor_id': vendor_id.id,
                                                                'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                                'vendor_amount_bill': 0.0,
                                                                'bill_paid': move_line_product.is_bill_paid, })


    
    def fetch_vendor_refunded_bills(self,fetch_refunded_bills):
        for record in fetch_refunded_bills:
            if record.state == 'posted' and record.payment_state in ("paid", "in_payment"):
                if record.reversed_entry_id.invoice_line_ids:
                    amount_paid = 0
                    for move_line_product in record.reversed_entry_id.invoice_line_ids:

                        if self.vendor_line_released_bucket_id.id == move_line_product.bucket_ids.id:
                            if move_line_product.product_id:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                    order="id desc")
                                vendor_id = vendor_id.partner_id
                            else:
                                vendor_id = self.vendor_id
                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                [('bill_name', '=', record.reversed_entry_id.id), ('vendor_id', '=', vendor_id.id),
                                 ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])

                            if not existing_bill_rec:
                                self.env['vendor.bill.detail'].sudo().create({
                                    'bill_name': record.reversed_entry_id.id,
                                    'vendor_id': vendor_id.id,
                                    "refund_bill_name": record.id,
                                    'vendor_line_released_from_user_bucket_id': self.id,
                                    'vendor_bill_amount_refunded': move_line_product.price_subtotal,
                                    'bill_paid': True,
                                    'debit':True,
                                    'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id
                                })
                            else:
                                existing_bill_rec.write({'bill_name': record.reversed_entry_id.id,
                                    'vendor_id': vendor_id.id,
                                    'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id,
                                    'vendor_amount_bill': 0.0,"refund_bill_name": record.id,
                                    'vendor_bill_amount_refunded': move_line_product.price_subtotal,
                                    'bill_paid': True,
                                    'debit': True,
                                })


            if record.state == 'posted' and record.payment_state == 'partial':
                if record.reversed_entry_id.invoice_line_ids:
                    amount_paid = 0
                    amount_bill = 0
                    for move_line_product in record.reversed_entry_id.invoice_line_ids:
                        if move_line_product.refund_residual_amount != 0.0:
                            if move_line_product.product_id:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                    order="id desc")
                                vendor_id = vendor_id.partner_id
                            else:
                                vendor_id = self.vendor_id
                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                [('bill_name', '=', record.reversed_entry_id.id), ('vendor_id', '=', vendor_id.id),
                                 ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])

                            if not existing_bill_rec:
                                self.env['vendor.bill.detail'].sudo().create({
                                    'bill_name': record.reversed_entry_id.id,"refund_bill_name": record.id,
                                    'vendor_id': vendor_id.id,
                                    'vendor_amount_bill': move_line_product.bill_residual_amount,
                                    'vendor_line_released_from_user_bucket_id': self.id,
                                    'vendor_bill_amount_refunded': move_line_product.price_subtotal - move_line_product.refund_residual_amount,
                                    'bill_paid': move_line_product.is_bill_paid,
                                    'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id
                                })
                            else:
                                existing_bill_rec.write({'bill_name': record.reversed_entry_id.id,'vendor_id': vendor_id.id,'vendor_amount_bill': move_line_product.bill_residual_amount,"refund_bill_name": record.id,
                                                            'vendor_bill_amount_refunded': move_line_product.price_subtotal - move_line_product.refund_residual_amount,
                                                            'bill_paid': move_line_product.is_bill_paid,
                                                         'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id

                                                         })
                        else:
                            if move_line_product.product_id:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                    order="id desc")
                                vendor_id = vendor_id.partner_id
                            else:
                                vendor_id = self.vendor_id
                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                [('bill_name', '=', record.reversed_entry_id.id), ('vendor_id', '=', vendor_id.id),
                                 ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                            if not existing_bill_rec:

                                self.env['vendor.bill.detail'].sudo().create({
                                    'bill_name': record.reversed_entry_id.id,"refund_bill_name": record.id,
                                    'vendor_id': vendor_id.id,
                                    'vendor_amount_bill': 0.0,
                                    'vendor_line_released_from_user_bucket_id': self.id,
                                    'vendor_bill_amount_refunded': move_line_product.price_subtotal,
                                    'bill_paid': move_line_product.is_bill_paid,
                                    'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id
                                })
                            else:

                                existing_bill_rec.write({
                                    'vendor_id': vendor_id.id,
                                    'bill_name': record.reversed_entry_id.id,
                                    'vendor_bill_amount_refunded': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                            'vendor_amount_bill': 0.0,"refund_bill_name": record.id,
                                                            'bill_paid': move_line_product.is_bill_paid,
                                    'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id
                                })


   
    def fetch_ven_bills_details_inside_user(self):
        fetch_bills = self.env['account.move'].sudo().search([('move_type', '=', "in_invoice")])
        fetch_refunded_bills = self.env['account.move'].sudo().search([('move_type', '=', "in_refund")])
        self.fetch_vendor_bills(fetch_bills)
        self.fetch_vendor_refunded_bills(fetch_refunded_bills)
        domain = [('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)]
        vals = {
            'name': _('Bill Detail'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'vendor.bill.detail',
        }
        return vals
    
    