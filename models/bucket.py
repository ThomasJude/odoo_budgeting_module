# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError


class Bucket(models.Model):
    _name = "bucket"
    
    name = fields.Char(string='Name')
    bucket_amount = fields.Float(string='Bucket Amount',)
    # user_type = fields.Selection([('vendor','Vendor'),('sales_rep','Sales Rep'),('workers','Workers'),('excess','Excess'),('etc','Etc')], "User Type")
    bucket_status = fields.Selection([('invoiced','Invoiced'),('released','Released')], "Bucket Status")
    bucket_type_id = fields.Many2one('bucket.type','Bucket Type')
    vendor_line = fields.One2many('vendor.line', 'vendor_line_bucket_id', 'Vendor Details')
    user_line = fields.One2many('user.line', 'user_line_bucket_id', 'User Details')
    vendor_line_released = fields.One2many('vendor.line.released', 'vendor_line_released_bucket_id', 'Vendor Released Details')
    user_line_released = fields.One2many('user.line.released', 'user_line_released_bucket_id', 'User Released Details')

    check = fields.Boolean(compute='_get_value')
    check2 = fields.Boolean(compute='_get_status')
    
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{} ({})".format(record.name, record.bucket_amount)))
        return result
    
    
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
            if rec.bucket_type_id.is_vendor:
                rec.check = True
                # rec._get_amount()
            else:
                rec.check = False
                # rec._get_amount()


    @api.depends('bucket_status')
    def _get_status(self):
        for rec in self:
            if rec.bucket_status == "invoiced":
                rec.check2 = True
            else:
                rec.check2 = False


class VendorLine(models.Model):
    _name = "vendor.line"
    
    vendor_id = fields.Many2one('res.partner','Vendors')
    vendor_line_bucket_id = fields.Many2one('bucket','bucket')
    total_amount = fields.Float('Total Amount')
    
    
    def fetch_vendor_bills_details(self):
        all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_inv_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False)])
        all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_inv_remaining_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False)])

        all_invoices = []
        for invoice_line in all_vendor_invoice_lines:
            all_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_vendor_remaining_lines:
            all_invoices.append(remaining_inv_line.prod_remaining_id)
        rem_duplicate_invoice_no_set = set(all_invoices)
        final_invoice_no = list(rem_duplicate_invoice_no_set)
        for invoices in final_invoice_no:
            if invoices.state == 'posted':
                if invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            total_paid_amount_inv += inv_budget_line.amount_residual
                            total_amount_inv += inv_budget_line.amount
                    all_fixed_amount_released = []

                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(invoices.inv_budget_line):
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                                total_amount_rel += product_remaining_budget_line.amount
                    else:
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                total_paid_amount_rel += product_remaining_budget_line.amount
                                total_amount_rel += product_remaining_budget_line.amount
                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    print("SCVVVVVVVV",total_vendor_paid_amount,total_vendor_amount_part_paid_per_invoice)
                    existing_record_1 = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id)])
                    if total_vendor_amount_part_paid_per_invoice != 0.0:
                        print("WCVE")
                        if existing_record_1:
                            print("EXE",total_vendor_amount_part_paid_per_invoice)
                            existing_record_1.write({'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})
                        else:
                            create_record = self.env['vendor.invoice.detail'].sudo().create(
                                {"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_bucket_id.bucket_type_id.id,
                                 'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})

                    else:
                        if existing_record_1:
                            existing_record_1.write({'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})
                        else:
                            self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_bucket_id.bucket_type_id.id,'released':True,'vendor_amount':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})

                else:
                    if not invoices.payment_state == 'posted':
                        total_vendor_amount = 0.0
                        total_amount_inv = 0.0
                        total_amount_rel = 0.0
                        for inv_budget_line in invoices.inv_budget_line:
                            # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                            if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                                total_amount_inv += inv_budget_line.amount
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                total_amount_rel += product_remaining_budget_line.amount

                        total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                        existing_record = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('vendor_id','=',self.vendor_id.id),('bucket_type_id','=',self.vendor_line_bucket_id.bucket_type_id.id)])
                        if not existing_record:
                            create_record = self.env['vendor.invoice.detail'].sudo().create({"vendor_id":self.vendor_id.id,'invoice_name':invoices.id,"bucket_type_id":self.vendor_line_bucket_id.bucket_type_id.id,'vendor_amount_invoiced':total_vendor_amount_per_invoice})
                    # else:
                    #     existing_record.write({'released': True})



        # VENDOR LINE PAID Invoices

        all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_inv_vendor_id.id', '=', self.vendor_id.id), ('released', '=', True)])
        all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_inv_remaining_vendor_id.id', '=', self.vendor_id.id), ('released', '=', True)])

        all_paid_invoices = []

        for invoice_line in all_vendor_invoice_lines:
            all_paid_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_vendor_remaining_lines:
            all_paid_invoices.append(remaining_inv_line.prod_remaining_id)

        rem_duplicate_paid_invoice_no_set = set(all_paid_invoices)
        final_paid_invoice_no = list(rem_duplicate_paid_invoice_no_set)
        for paid_invoices in final_paid_invoice_no:
            if paid_invoices.state == 'posted':

                # vendor paid Invoices
                if paid_invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            total_paid_amount_inv += inv_budget_line.amount_residual
                            total_amount_inv += inv_budget_line.amount
                    all_fixed_amount_released_paid = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released_paid.append(inv_budget_line.id)
                    if len(all_fixed_amount_released_paid) == len(paid_invoices.inv_budget_line):
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                                total_amount_rel += product_remaining_budget_line.amount
                    else:
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                total_paid_amount_rel += product_remaining_budget_line.amount
                                total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    print("EBBBBBBB",total_vendor_paid_amount,total_vendor_amount_part_paid_per_invoice)
                    existing_record_1 = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id)])
                    if total_vendor_amount_part_paid_per_invoice != 0.0:
                        print("ECCC",total_vendor_amount_part_paid_per_invoice)
                        if existing_record_1:
                            existing_record_1.write(
                                {'vendor_amount_invoiced': total_vendor_amount_part_paid_per_invoice,
                                 'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_vendor_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice})
                        else:
                            create_record = self.env['vendor.invoice.detail'].sudo().create(
                                {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                                 'bucket_type_id': self.vendor_line_bucket_id.bucket_type_id.id,
                                 'vendor_amount_invoiced': total_vendor_amount_part_paid_per_invoice,
                                 'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_vendor_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice})

                    else:
                        if existing_record_1:
                            existing_record_1.write(
                                {'released': True, 'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0,
                                 'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice})
                        else:
                            self.env['vendor.invoice.detail'].sudo().create(
                                {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                                 'bucket_type_id': self.vendor_line_bucket_id.bucket_type_id.id, 'released': True,
                                 'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                                 'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice})
                else:
                    print("Fully PAID INVOICE VENDOR 1")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                        if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                         ('bucket_type_id', '=', self.vendor_line_bucket_id.bucket_type_id.id)])
                    print("SXCCCCCCCCCCCC",existing_record)
                    if not existing_record:
                        create_record = self.env['vendor.invoice.detail'].sudo().create(
                            {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                             "bucket_type_id": self.vendor_line_bucket_id.bucket_type_id.id,
                             'released':True,
                             'vendor_amount_released': total_vendor_amount_per_invoice,
                             'vendor_amount_invoiced': 0.0})
                    else:
                        existing_record.write({'vendor_amount_released': total_vendor_amount_per_invoice,
                             'vendor_amount_invoiced': 0.0,'released':True})

                    # paid_existing_record = self.env['vendor.invoice.detail'].sudo().search(
                    #     [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_bucket_id.bucket_type_id.id)])
                    # print("@@@@@@@@@@@@@!$$$$$$$$$$$$$$$$4", paid_existing_record)
                    # paid_existing_record.write({'released': True})


        return {
            'name': _('Show In Detail'),
            'domain': [('vendor_id', '=', self.vendor_id.id),('released','=',False),('vendor_amount_invoiced','>',0.0)],
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            # 'target':'new',
            'res_model': 'vendor.invoice.detail',
        }


class VendorLineReleased(models.Model):
    _name = "vendor.line.released"

    vendor_id = fields.Many2one('res.partner', 'Vendors')
    vendor_line_released_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount = fields.Float('Total Amount')


    def fetch_vendor_paid_bills_details(self):

        all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_inv_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False)])
        all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_inv_remaining_vendor_id.id', '=', self.vendor_id.id), ('released', '=', False)])

        all_invoices = []
        for invoice_line in all_vendor_invoice_lines:
            all_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_vendor_remaining_lines:
            all_invoices.append(remaining_inv_line.prod_remaining_id)
        rem_duplicate_invoice_no_set = set(all_invoices)
        final_invoice_no = list(rem_duplicate_invoice_no_set)
        print("@!!!! 11", final_invoice_no)
        for invoices in final_invoice_no:
            if invoices.state == 'posted':
                print("@!!!!",invoices)
                # DRAFT
                if invoices.payment_state == 'partial':
                    print('partial')
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            total_paid_amount_inv += inv_budget_line.amount_residual
                            total_amount_inv += inv_budget_line.amount
                    all_fixed_amount_released = []
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(invoices.inv_budget_line):
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                                total_amount_rel += product_remaining_budget_line.amount
                    else:
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                total_paid_amount_rel += product_remaining_budget_line.amount
                                total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    print("UUUUUUUUUUU",total_vendor_amount_part_paid_per_invoice,total_vendor_paid_amount)
                    existing_record_2 = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', invoices.id), ('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                    if total_vendor_amount_part_paid_per_invoice != 0.0:
                        print("WORKING PARTIAL11",existing_record_2)

                        if existing_record_2:
                            print('ssSS',total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice)
                            existing_record_2.write({'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})
                        else:
                            vals = {"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id,
                                 'vendor_amount_invoiced':total_vendor_amount_part_paid_per_invoice,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice,'partial_due_amount':total_vendor_amount_part_paid_per_invoice,'partial_paid_amount':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice}
                            create_record = self.env['vendor.invoice.detail'].sudo().create(vals)
                            # print("WCCVVVVVVVVVVVVVVVVVVVVV",vals,create_record.id)
                    else:
                        print("WORKING PARTIAL 22")

                        if existing_record_2:
                            existing_record_2.write({'released':True,'vendor_amount_invoiced':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})
                        else:
                            self.env['vendor.invoice.detail'].sudo().create({"vendor_id": self.vendor_id.id, 'invoice_name': invoices.id,'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id,'released':True,'vendor_amount':0.0,'partial_due_amount':0.0,'partial_paid_amount':0.0,'vendor_amount_released':total_vendor_paid_amount-total_vendor_amount_part_paid_per_invoice})

                else:
                    print('vendor else')
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in invoices.product_remaining_budget_line:
                        # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                        if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['vendor.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('vendor_id','=',self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                    if not existing_record:
                        create_record = self.env['vendor.invoice.detail'].sudo().create({"vendor_id":self.vendor_id.id,'invoice_name':invoices.id,"bucket_type_id":self.vendor_line_released_bucket_id.bucket_type_id.id,'vendor_amount_invoiced':total_vendor_amount_per_invoice})

        # VENDOR LINE PAID Invoices

        all_vendor_invoice_lines = self.env['invoice.budget.line'].sudo().search(
            [('budget_inv_vendor_id.id', '=', self.vendor_id.id), ('released', '=', True)])
        all_vendor_remaining_lines = self.env['product.budget.remaining'].sudo().search(
            [('budget_inv_remaining_vendor_id.id', '=', self.vendor_id.id), ('released', '=', True)])

        all_paid_invoices = []

        for invoice_line in all_vendor_invoice_lines:
            all_paid_invoices.append(invoice_line.prod_inv_id)
        for remaining_inv_line in all_vendor_remaining_lines:
            all_paid_invoices.append(remaining_inv_line.prod_remaining_id)

        rem_duplicate_paid_invoice_no_set = set(all_paid_invoices)
        final_paid_invoice_no = list(rem_duplicate_paid_invoice_no_set)
        print(final_paid_invoice_no,"@@@@@########")
        for paid_invoices in final_paid_invoice_no:
            if paid_invoices.state == 'posted':

                # vendor paid Invoices
                if paid_invoices.payment_state == 'partial':
                    print('partially paid')
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            total_paid_amount_inv += inv_budget_line.amount_residual
                            total_amount_inv += inv_budget_line.amount
                    all_fixed_amount_released_paid = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released_paid.append(inv_budget_line.id)
                    if len(all_fixed_amount_released_paid) == len(paid_invoices.inv_budget_line):
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                                total_amount_rel += product_remaining_budget_line.amount
                    else:
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                total_paid_amount_rel += product_remaining_budget_line.amount
                                total_amount_rel += product_remaining_budget_line.amount
                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                    print("WWWWWWWW", total_vendor_amount_part_paid_per_invoice, existing_record_1)
                    if total_vendor_amount_part_paid_per_invoice != 0.0:
                        if existing_record_1:
                            print('ssSS', total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice)
                            existing_record_1.write(
                                {'vendor_amount_invoiced': total_vendor_amount_part_paid_per_invoice,
                                 'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_vendor_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice})
                        else:
                            create_record = self.env['vendor.invoice.detail'].sudo().create(
                                {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                                 'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id,
                                 'vendor_amount_invoiced': total_vendor_amount_part_paid_per_invoice,
                                 'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_vendor_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice})

                    else:
                        if existing_record_1:
                            existing_record_1.write(
                                {'released': True, 'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0,
                                 'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice})
                        else:
                            self.env['vendor.invoice.detail'].sudo().create(
                                {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                                 'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id, 'released': True,
                                 'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                                 'vendor_amount_released': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice})
                else:
                    print("Fully PAID INVOICE VENDOR 11111")

                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                        if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('vendor_id', '=', self.vendor_id.id),
                         ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                    print("SXXVHHHHHHHHHHHHHH",existing_record,total_vendor_amount_per_invoice)
                    if not existing_record:
                        create_record = self.env['vendor.invoice.detail'].sudo().create(
                            {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.id,
                             "bucket_type_id": self.vendor_line_released_bucket_id.bucket_type_id.id,
                             'released':True,'vendor_amount_released': total_vendor_amount_per_invoice,
                             'vendor_amount_invoiced':0.0})
                    else:
                        existing_record.write({'vendor_amount_released':total_vendor_amount_per_invoice,'released':True,'vendor_amount_invoiced':0.0})

        domain = ['|',('released','=',True),('partial_due_amount','>',0.0),('vendor_id', '=', self.vendor_id.id),('vendor_amount_released','>',0.0)]
        vals = {
            'name': _('Show In Detail'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            # 'target':'new',
            'res_model': 'vendor.invoice.detail',
        }
        return vals


class UserLine(models.Model):
    _name = "user.line"


    user_id = fields.Many2one('res.users', 'Users')
    user_line_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount = fields.Float('Total Amount')



    def fetch_user_bills_details(self):
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
        print("@!!!! user invoiced", final_invoice_no)
        for invoices in final_invoice_no:
            if invoices.state == 'posted':
                print("@!!!! user")

                if invoices.payment_state == 'partial':
                    print("WWWWWWWWWXXXXXXXXXXXXXXXXXX")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                            total_paid_amount_inv += inv_budget_line.amount_residual

                    all_fixed_amount_released = []
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(invoices.inv_budget_line):

                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    else:
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount

                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', invoices.id), ('user_id', '=', self.user_id.id),('bucket_type_id','=',self.user_line_bucket_id.bucket_type_id.id)])
                    print("WWWWWWWW user",total_vendor_paid_amount, total_user_amount_part_paid_per_invoice)
                    if total_user_amount_part_paid_per_invoice != 0.0:
                        print("seeee user",existing_record_1)
                        if existing_record_1:
                            print('ssSS', total_vendor_paid_amount - total_user_amount_part_paid_per_invoice)
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
                    print("WORKING else par")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in invoices.product_remaining_budget_line:
                        # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('user_id','=',self.user_id.id),('bucket_type_id','=',self.user_line_bucket_id.bucket_type_id.id)])
                    print("EXISTING",existing_record,self.user_line_bucket_id.id)
                    if not existing_record:
                        create_record = self.env['user.invoice.detail'].sudo().create({"user_id":self.user_id.id,"bucket_type_id":self.user_line_bucket_id.bucket_type_id.id,'invoice_name':invoices.id,'user_amount_invoiced':total_vendor_amount_per_invoice})

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
        print("released Invoices user line",final_paid_invoice_no)
        for paid_invoices in final_paid_invoice_no:
            if paid_invoices.state == 'posted':
                print('inside user line paid invoice partial')
                if paid_invoices.payment_state == 'partial':

                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                            total_paid_amount_inv += inv_budget_line.amount_residual

                    all_fixed_amount_released_paid = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released_paid.append(inv_budget_line.id)
                    if len(all_fixed_amount_released_paid) == len(paid_invoices.inv_budget_line):

                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    else:
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount
                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_bucket_id.bucket_type_id.id)])
                    print("WWWWWWWW user paid", total_vendor_paid_amount, total_user_amount_part_paid_per_invoice)
                    if total_user_amount_part_paid_per_invoice != 0.0:
                        print("seeee user", )
                        if existing_record_1:
                            print('ssSS', total_vendor_paid_amount - total_user_amount_part_paid_per_invoice)
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
                    print("Fully PAID INVOICE USER")

                    print("else not partial")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_bucket_id.bucket_type_id.id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_bucket_id.bucket_type_id.id)])
                    print("EXISTING 111122222", existing_record, total_vendor_amount_per_invoice)
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
        return {
                'name': _('Show In Detail'),
                'domain': [('user_id', '=', self.user_id.id),('released','=',False),('bucket_type_id','=',self.user_line_bucket_id.bucket_type_id.id),('user_amount_invoiced','>',0.0)],
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                # 'target': 'new',
                'res_model': 'user.invoice.detail',
            }



class UserLineReleased(models.Model):
    _name = "user.line.released"

    user_id = fields.Many2one('res.users', 'Users')
    user_line_released_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount = fields.Float('Total Amount')

    def fetch_user_paid_bills_details(self):
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
        print("@!!!! user released", final_invoice_no)
        for invoices in final_invoice_no:
            if invoices.state == 'posted' :
                print("@!!!! user",invoices.payment_state)
                if invoices.payment_state == 'partial':
                    print("WWWWWWWWWXXXXXXXXXXXXXXXXXX")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                            total_paid_amount_inv += inv_budget_line.amount_residual
                    all_fixed_amount_released = []
                    for inv_budget_line in invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released.append(inv_budget_line.id)
                    if len(all_fixed_amount_released) == len(invoices.inv_budget_line):
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    else:
                        for product_remaining_budget_line in invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount

                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', invoices.id), ('user_id', '=', self.user_id.id),('bucket_type_id','=',self.user_line_released_bucket_id.bucket_type_id.id)])
                    print("WWWWWWWW user",existing_record_1, total_user_amount_part_paid_per_invoice)
                    if total_user_amount_part_paid_per_invoice != 0.0:
                        print("seeee user",)
                        if existing_record_1:
                            print('ssSS', total_vendor_paid_amount - total_user_amount_part_paid_per_invoice)
                            existing_record_1.write(
                                {'user_amount_invoiced': total_user_amount_part_paid_per_invoice,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                 'partial_due_amount': total_user_amount_part_paid_per_invoice,
                                 'partial_paid_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            create_record = self.env['user.invoice.detail'].sudo().create(
                                {"user_id": self.user_id.id, 'invoice_name': invoices.id,
                                 'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id,
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
                                 'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id, 'released': True,
                                 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})



                else:
                    print("WORKING else par")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in invoices.product_remaining_budget_line:
                        # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search([('invoice_name','=',invoices.id),('user_id','=',self.user_id.id),('bucket_type_id','=',self.user_line_released_bucket_id.bucket_type_id.id)])
                    print("EXISTING",existing_record,self.user_line_released_bucket_id.id)
                    if not existing_record:

                        create_record = self.env['user.invoice.detail'].sudo().create({"user_id":self.user_id.id,"bucket_type_id":self.user_line_released_bucket_id.bucket_type_id.id,'invoice_name':invoices.id,'user_amount_invoiced':total_vendor_amount_per_invoice})




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
        print("released Invoices", final_paid_invoice_no)
        for paid_invoices in final_paid_invoice_no:
            print(paid_invoices.payment_state)
            if paid_invoices.state == 'posted':
                if paid_invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                            total_paid_amount_inv += inv_budget_line.amount_residual
                    all_fixed_amount_released_paid = []
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        if inv_budget_line.released:
                            all_fixed_amount_released_paid.append(inv_budget_line.id)
                    if len(all_fixed_amount_released_paid) == len(paid_invoices.inv_budget_line):
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount_residual
                    else:
                        for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount

                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_released_bucket_id.bucket_type_id.id)])
                    print("WWWWWWWW user paid",paid_invoices.id, existing_record_1, total_user_amount_part_paid_per_invoice)
                    if total_user_amount_part_paid_per_invoice != 0.0:
                        print("seeee user", )
                        if existing_record_1:
                            print('ssSS', total_vendor_paid_amount - total_user_amount_part_paid_per_invoice)
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
                        if existing_record_1:
                            existing_record_1.write(
                                {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            self.env['user.invoice.detail'].sudo().create(
                                {"user_id": self.user_id.id, 'invoice_name': paid_invoices.id,
                                 'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id, 'released': True,
                                 'user_amount': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                                 'user_amount_released': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})

                else:
                    print("else not partial")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.product_remaining_budget_line:
                        # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_released_bucket_id.bucket_type_id.id)])
                    print("EXISTING 111122222",paid_invoices.id, existing_record, self.user_line_released_bucket_id.id)
                    if not existing_record:
                        create_record = self.env['user.invoice.detail'].sudo().create({"user_id": self.user_id.id,
                                                                                       "bucket_type_id": self.user_line_released_bucket_id.bucket_type_id.id,
                                                                                       'invoice_name': paid_invoices.id,
                                                                                       'released':True,
                                                                                       'user_amount_released': total_vendor_amount_per_invoice,
                                                                                       'user_amount_invoiced': 0.0,
                                                                                       })

                    else:
                        # print(total_vendor_amount_per_invoice)
                        existing_record.write(
                            {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                             'partial_paid_amount': 0.0,
                             'user_amount_released': total_vendor_amount_per_invoice})

        domain = ['|',('released','=',True),('partial_due_amount','>',0.0),('user_id', '=', self.user_id.id),('user_amount_released','>',0.0),('bucket_type_id','=',self.user_line_released_bucket_id.bucket_type_id.id)]

        return {
            'name': _('Show In Detail'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            # 'target': 'new',
            'res_model': 'user.invoice.detail',
        }