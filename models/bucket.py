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

    vendor_line_released_inside_user = fields.One2many('vendor.line.released.inside.user',"vendor_line_released_bucket_id","Vendor Bill Details")

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
    
    def fetch_vendor_invoiced_bill_inv_show(self):
        return {
            'name': "Invoice Visibility",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'invoice.visibility.wiz',
            'view_id': self.env.ref('odoo_budgeting_module.invoice_visibility_wiz_form').id,
            'target': 'new',
                }
    
    
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
            'target':'new',
            'res_model': 'vendor.invoice.detail',
        }


class VendorLineReleased(models.Model):
    _name = "vendor.line.released"

    vendor_id = fields.Many2one('res.partner', 'Vendors')
    vendor_line_released_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount = fields.Float('Total Amount')
    
    
    def fetch_vendor_bill_inv_show(self):
        return {
            'name': "Invoice/Bill Visibility",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'invoice.bill.wiz',
            'view_id': self.env.ref('odoo_budgeting_module.invoice_bill_wiz_form').id,
            'target': 'new',
                }
        
        
    
    
    
    def fetch_ven_bill_details(self):
        fetch_bills = self.env['account.move'].sudo().search([('move_type','=',"in_invoice")])

        for record in fetch_bills:
            if record.state == 'posted' and record.payment_state in ("paid","in_payment"):
                if record.invoice_line_ids:
                    for move_line_product in record.invoice_line_ids:
                        # if len(move_line_product.bucket_ids)>1:
                        #     print("SFVVVVVVVV",record.id)
                        #     # for buckets in move_line_product.bucket_ids:
                        #     vendor_id = self.env["product.supplierinfo"].sudo().search(
                        #         [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                        #         limit=1, order="id desc")
                        #     existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                        #         [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                        #          ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                        #     vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.partner_id.id), (
                        #     'vendor_line_released_bucket_id', '=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                        #     if not existing_bill_rec:
                        #         self.env['vendor.bill.detail'].sudo().create({
                        #             'bill_name': record.id,
                        #             'vendor_id': vendor_id.partner_id.id,
                        #             # 'vendor_amount_bill':move_line_product.price_subtotal,
                        #             'vendor_line_released_id': vendor_line_released_id.id,
                        #             'vendor_amount_paid': move_line_product.price_subtotal,
                        #             'bill_paid': True,
                        #             'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id
                        #         })
                        #     else:
                        #         existing_bill_rec.write({
                        #             'vendor_amount_bill': 0.0,
                        #             'vendor_amount_paid': move_line_product.price_subtotal,
                        #             'bill_paid': True,
                        #         })
                        # else:
                        #     print("ELSE 123456",self.vendor_line_released_bucket_id.bucket_type_id.id)

                            # if self.vendor_line_released_bucket_id.id == move_line_product.bucket_ids.id:

                        vendor_id = self.env["product.supplierinfo"].sudo().search([('product_tmpl_id','=',move_line_product.product_id.product_tmpl_id.id)],limit=1,order="id desc")
                        existing_bill_rec = self.env['vendor.bill.detail'].sudo().search([('bill_name','=',record.id),('vendor_id','=',vendor_id.partner_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                        vendor_line_released_id = self.search([('vendor_id','=',vendor_id.partner_id.id),('vendor_line_released_bucket_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                        if not existing_bill_rec:
                            self.env['vendor.bill.detail'].sudo().create({
                                        'bill_name':record.id,
                                        'vendor_id':vendor_id.partner_id.id,
                                        # 'vendor_amount_bill':move_line_product.price_subtotal,
                                        'vendor_line_released_id':vendor_line_released_id.id,
                                        'vendor_amount_paid':move_line_product.price_subtotal,
                                        'bill_paid':True,
                                        'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id
                                    })
                        else:
                            existing_bill_rec.write({
                                'vendor_amount_bill':0.0,
                                'vendor_amount_paid': move_line_product.price_subtotal,
                                'bill_paid': True,
                            })

                        # existing_bill_rec = self.env['vendor.bill.detail'].sudo().search([('bill_name','=',record.id),('vendor_id','=',self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id)])
                        # if not existing_bill_rec:
                        #     self.env['vendor.bill.detail'].sudo().create({
                        #         'bill_name':record.id,
                        #         'vendor_id':
                        #     })
            if record.state == 'posted' and record.payment_state == 'partial':
                if record.invoice_line_ids:
                    for move_line_product in record.invoice_line_ids:
                        # if len(move_line_product.bucket_ids) > 1:
                        #     print("SFVVVVVVVV", record.id)
                        # else:

                        if move_line_product.bill_residual_amount != 0.0:
                            if not move_line_product.is_bill_paid:
                                print("11111111111111111111")
                                vendor_id = self.env["product.supplierinfo"].sudo().search([('product_tmpl_id','=',move_line_product.product_id.product_tmpl_id.id)],limit=1,order="id desc")
                                existing_bill_rec = self.env['vendor.bill.detail'].sudo().search([('bill_name','=',record.id),('vendor_id','=',vendor_id.partner_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)])
                                vendor_line_released_id = self.search([('vendor_id','=',vendor_id.partner_id.id)])
                                if not existing_bill_rec:
                                    print("333333333333333")

                                    self.env['vendor.bill.detail'].sudo().create({
                                                'bill_name':record.id,
                                                'vendor_id':vendor_id.partner_id.id,
                                                'vendor_amount_bill':move_line_product.price_subtotal,
                                                'vendor_line_released_id':vendor_line_released_id.id,
                                                'vendor_amount_paid':move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                'bill_paid':move_line_product.is_bill_paid,
                                                'bucket_type_id':self.vendor_line_released_bucket_id.bucket_type_id.id
                                            })
                                else:
                                    print("4444444444444444444444",move_line_product.price_subtotal,move_line_product.bill_residual_amount)

                                    existing_bill_rec.write({'vendor_amount_paid':move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                             'bill_paid':move_line_product.is_bill_paid})
                            else:
                                print("BBBBBBBBBBBBBB")
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                    limit=1, order="id desc")
                                existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                    [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                                     ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                                vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.partner_id.id)])
                                if not existing_bill_rec:
                                    print("RRRRRRRRRRRR")

                                    self.env['vendor.bill.detail'].sudo().create({
                                        'bill_name': record.id,
                                        'vendor_id': vendor_id.partner_id.id,
                                        'vendor_amount_bill': 0.0,
                                        'vendor_line_released_id': vendor_line_released_id.id,
                                        'vendor_amount_paid': move_line_product.price_subtotal,
                                        'bill_paid': move_line_product.is_bill_paid,
                                        'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id
                                    })
                                else:
                                    print("TTTTTTTTTTTTTTTTt", move_line_product.price_subtotal,
                                          move_line_product.bill_residual_amount)

                                    existing_bill_rec.write({'vendor_amount_paid': move_line_product.price_subtotal,
                                                                'bill_paid': move_line_product.is_bill_paid})
                        else:
                            print("22222222222222222")
                            if move_line_product.is_bill_paid:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                    order="id desc")
                                existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                    [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                                     ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                                vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.partner_id.id)])
                                if not existing_bill_rec:
                                    self.env['vendor.bill.detail'].sudo().create({
                                        'bill_name': record.id,
                                        'vendor_id': vendor_id.partner_id.id,
                                        'vendor_amount_bill':0.0,
                                        'vendor_line_released_id': vendor_line_released_id.id,
                                        'vendor_amount_paid': move_line_product.price_subtotal,
                                        'bill_paid': move_line_product.is_bill_paid,
                                        'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id
                                    })
                                else:
                                    print('RTTTTTTYYYYYYyy',move_line_product.price_subtotal,move_line_product.bill_residual_amount)

                                    existing_bill_rec.write({'vendor_amount_paid':move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                             'vendor_amount_bill':0.0,
                                                             'bill_paid':move_line_product.is_bill_paid,})

        domain = [('vendor_id','=',self.vendor_id.id),("debit",'=',False),('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)]

        vals = {
            'name': _('Show Bill Detail'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'target':'new',
            'res_model': 'vendor.bill.detail',
        }
        return vals


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
            refund_invoice_id = self.env["account.move"].sudo().search([('reversed_entry_id', '=', invoices.id)])

            if invoices.state == 'posted' and invoices.move_type == "out_invoice" and not refund_invoice_id:
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
        refunded_invoices = self.env["account.move"].sudo().search([('reversed_entry_id', '!=', False)])
        for refunded_invoice in refunded_invoices:
            all_paid_invoices.append(refunded_invoice)
        rem_duplicate_paid_invoice_no_set = set(all_paid_invoices)
        final_paid_invoice_no = list(rem_duplicate_paid_invoice_no_set)

        for paid_invoices in final_paid_invoice_no:
            refunded_invoice_id = self.env["account.move"].sudo().search([('reversed_entry_id', '=', paid_invoices.id)])
            if paid_invoices.state == 'posted' and paid_invoices.move_type == 'out_invoice' and not refunded_invoice_id:
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
            if paid_invoices.state == 'posted' and paid_invoices.move_type == 'out_refund':
                print("STATE",paid_invoices.payment_state,paid_invoices.id)
                if paid_invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    vendor_id_check = False
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            vendor_id_check=True
                            total_paid_amount_inv += inv_budget_line.refund_residual
                            total_amount_inv += inv_budget_line.amount
                    all_fixed_amount_released_paid = []
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        if inv_budget_line.item_refunded:
                            all_fixed_amount_released_paid.append(inv_budget_line.item_refunded)
                    print(all_fixed_amount_released_paid)
                    if len(all_fixed_amount_released_paid) == len(paid_invoices.reversed_entry_id.inv_budget_line):
                        for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:

                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                vendor_id_check = True
                                total_paid_amount_rel += product_remaining_budget_line.refund_residual
                                total_amount_rel += product_remaining_budget_line.amount
                    else:
                        print("INSIDE PRODUCT REMAINING ELSE",)
                        for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            print("INSIDE PRODUCT ELSE",product_remaining_budget_line.budget_inv_remaining_vendor_id,self.vendor_id)
                            if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                                print("product_remaining_budget_line",product_remaining_budget_line.amount)
                                vendor_id_check = True
                                total_paid_amount_rel += product_remaining_budget_line.amount
                                total_amount_rel += product_remaining_budget_line.amount
                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_vendor_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    print("WWWWWWWWWWWWWEEEEEEEEEE",total_vendor_paid_amount,total_vendor_amount_part_paid_per_invoice)

                    existing_record_1 = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.reversed_entry_id.id), ('vendor_id', '=', self.vendor_id.id),
                         ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])

                    if total_vendor_amount_part_paid_per_invoice != 0.0:
                        print("RRRRRRRRRR",existing_record_1,vendor_id_check)
                        if existing_record_1 and vendor_id_check:
                            print('ssSS', total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice)
                            existing_record_1.write(
                                {'released':True,
                                'refunded_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                 'vendor_amount_released': total_vendor_amount_part_paid_per_invoice,
                                 })
                        else:
                            if vendor_id_check:
                                print("REFUNDED SSSS")
                                create_record = self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,'refunded_invoice_name':paid_invoices.id,
                                     'released':True,
                                     'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id,
                                     'vendor_amount_released': total_vendor_amount_part_paid_per_invoice,
                                     'refunded_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                     })

                    else:
                        print("inside_else",total_vendor_paid_amount,total_vendor_amount_part_paid_per_invoice)
                        if existing_record_1 and vendor_id_check:
                            existing_record_1.vendor_amount_released = 0.0
                            existing_record_1.write(
                                {'released': True,
                                 'refunded_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                 })
                        else:
                            if vendor_id_check:
                                self.env['vendor.invoice.detail'].sudo().create(
                                    {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,'refunded_invoice_name':paid_invoices.id,
                                     'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id,
                                     'released': True,
                                     'vendor_amount_invoiced': 0.0, 'partial_due_amount': 0.0, 'partial_paid_amount': 0.0,
                                     'vendor_amount_released': 0.0,
                                     'refunded_amount': total_vendor_paid_amount - total_vendor_amount_part_paid_per_invoice,
                                     })

                else:
                    print("inside main else")
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    vendor_id_check = False
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_inv_vendor_id in self.vendor_id:
                            vendor_id_check = True
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                        # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                        if product_remaining_budget_line.budget_inv_remaining_vendor_id in self.vendor_id:
                            vendor_id_check = True
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv

                    existing_record = self.env['vendor.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.reversed_entry_id.id), ('vendor_id', '=', self.vendor_id.id),
                         ('bucket_type_id', '=', self.vendor_line_released_bucket_id.bucket_type_id.id)])
                    if not existing_record and vendor_id_check:
                        create_record = self.env['vendor.invoice.detail'].sudo().create(
                            {"vendor_id": self.vendor_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,'refunded_invoice_name':paid_invoices.id,
                             "bucket_type_id": self.vendor_line_released_bucket_id.bucket_type_id.id,
                             'released': True, 'vendor_amount_released': 0.0,
                             'vendor_amount_invoiced': 0.0,'refunded_amount':total_vendor_amount_per_invoice})
                    else:
                        if vendor_id_check:
                            existing_record.write(
                                {'vendor_amount_released': 0.0, 'released': True,
                                 'vendor_amount_invoiced': 0.0,'refunded_amount':total_vendor_amount_per_invoice})

        domain = ['|',('released','=',True),('partial_due_amount','>',0.0),('vendor_id', '=', self.vendor_id.id),('vendor_amount_released','>=',0.0)]
        vals = {
            'name': _('Show In Detail'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'target':'new',
            'res_model': 'vendor.invoice.detail',
        }
        return vals



class UserLine(models.Model):
    _name = "user.line"


    user_id = fields.Many2one('res.users', 'Users')
    user_line_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount = fields.Float('Total Amount')
    
    def fetch_user_invoiced_bill_inv_show(self):
        return {
            'name': "Invoice Visibility",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'user.invoice.visibility.wiz',
            'view_id': self.env.ref('odoo_budgeting_module.user_invoice_visibility_wiz_form').id,
            'target': 'new',
                }



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
                'target': 'new',
                'res_model': 'user.invoice.detail',
            }



class UserLineReleased(models.Model):
    _name = "user.line.released"

    user_id = fields.Many2one('res.users', 'Users')
    user_line_released_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount = fields.Float('Total Amount')
    
    def fetch_user_released_bill_inv_show(self):
        return {
            'name': "Invoice Visibility",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'user.invoice.visibility.wiz',
            'view_id': self.env.ref('odoo_budgeting_module.user_invoice_visibility_wiz_form').id,
            'target': 'new',
                }

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
            refund_invoice_id = self.env["account.move"].sudo().search([('reversed_entry_id', '=', invoices.id)])
            if invoices.state == 'posted' and not refund_invoice_id:
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
        refunded_invoices = self.env["account.move"].sudo().search([('reversed_entry_id', '!=', False)])
        for refunded_invoice in refunded_invoices:
            all_paid_invoices.append(refunded_invoice)
        rem_duplicate_paid_invoice_no_set = set(all_paid_invoices)
        final_paid_invoice_no = list(rem_duplicate_paid_invoice_no_set)
        for paid_invoices in final_paid_invoice_no:
            print(paid_invoices.payment_state)
            refunded_invoice_id = self.env["account.move"].sudo().search([('reversed_entry_id', '=', paid_invoices.id)])
            if paid_invoices.state == 'posted' and paid_invoices.move_type == 'out_invoice' and not refunded_invoice_id:
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
            if paid_invoices.state == 'posted' and paid_invoices.move_type == 'out_refund':
                print("USER INVOICE STATE",paid_invoices.payment_state)
                user_id_check = False
                if paid_invoices.payment_state == 'partial':
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    total_paid_amount_inv = 0.0
                    total_paid_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_inv += inv_budget_line.amount
                            total_paid_amount_inv += inv_budget_line.refund_residual
                    all_fixed_amount_released_paid = []
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        if inv_budget_line.item_refunded:
                            all_fixed_amount_released_paid.append(inv_budget_line.id)
                    if len(all_fixed_amount_released_paid) == len(paid_invoices.inv_budget_line):
                        for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                user_id_check = True
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.refund_residual
                    else:
                        for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                            # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                            if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                                user_id_check = True
                                total_amount_rel += product_remaining_budget_line.amount
                                total_paid_amount_rel += product_remaining_budget_line.amount

                    total_vendor_paid_amount = total_amount_inv + total_amount_rel
                    total_user_amount_part_paid_per_invoice = total_paid_amount_inv + total_paid_amount_rel
                    existing_record_1 = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.reversed_entry_id.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_released_bucket_id.bucket_type_id.id)])
                    print("VENODR PAID AMOUNT",total_user_amount_part_paid_per_invoice,paid_invoices.reversed_entry_id.id,paid_invoices.id)
                    if total_user_amount_part_paid_per_invoice != 0.0:
                        if existing_record_1 and user_id_check:
                            existing_record_1.write(
                                {'released': True,
                                 'user_amount_released': total_user_amount_part_paid_per_invoice,
                                'refunded_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            if user_id_check:
                                create_record = self.env['user.invoice.detail'].sudo().create(
                                    {"user_id": self.user_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,'refunded_invoice_name':paid_invoices.id,
                                     'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id,
                                     'released': True,
                                     'user_amount_released': total_user_amount_part_paid_per_invoice,
                                     'refunded_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})

                    else:
                        print("paid this vendor",total_vendor_paid_amount,existing_record_1)
                        if existing_record_1 and user_id_check:
                            existing_record_1.write(
                                {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0,'user_amount_released': 0.0,
                                 'refunded_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice})
                        else:
                            if user_id_check:
                                self.env['user.invoice.detail'].sudo().create(
                                    {"user_id": self.user_id.id, 'invoice_name': paid_invoices.reversed_entry_id.id,'refunded_invoice_name':paid_invoices.id,
                                     'bucket_type_id': self.user_line_released_bucket_id.bucket_type_id.id,
                                     'released': True,
                                     'partial_due_amount': 0.0, 'refunded_amount': total_vendor_paid_amount - total_user_amount_part_paid_per_invoice,
                                     'user_amount_released': 0.0})

                else:
                    total_vendor_amount = 0.0
                    total_amount_inv = 0.0
                    total_amount_rel = 0.0
                    for inv_budget_line in paid_invoices.reversed_entry_id.inv_budget_line:
                        # if inv_budget_line.budget_inv_vendor_ids in self.vendor_id:
                        if inv_budget_line.budget_user_id.id == self.user_id.id and inv_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_inv += inv_budget_line.amount
                    for product_remaining_budget_line in paid_invoices.reversed_entry_id.product_remaining_budget_line:
                        # if product_remaining_budget_line.budget_inv_remaining_vendor_ids in self.vendor_id:
                        if product_remaining_budget_line.budget_remaining_user_id.id == self.user_id.id and product_remaining_budget_line.bucket_type_id.id == self.user_line_released_bucket_id.bucket_type_id.id:
                            user_id_check = True
                            total_amount_rel += product_remaining_budget_line.amount

                    total_vendor_amount_per_invoice = total_amount_rel + total_amount_inv
                    existing_record = self.env['user.invoice.detail'].sudo().search(
                        [('invoice_name', '=', paid_invoices.reversed_entry_id.id), ('user_id', '=', self.user_id.id),
                         ('bucket_type_id', '=', self.user_line_released_bucket_id.bucket_type_id.id)])
                    if not existing_record and user_id_check:
                        create_record = self.env['user.invoice.detail'].sudo().create({"user_id": self.user_id.id,
                                                                                       "bucket_type_id": self.user_line_released_bucket_id.bucket_type_id.id,
                                                                                       'invoice_name': paid_invoices.reversed_entry_id.id,'refunded_invoice_name':paid_invoices.id,
                                                                                       'released': True,
                                                                                       'user_amount_released': 0.0,
                                                                                       'user_amount_invoiced': 0.0,
                                                                                       'refunded_amount':total_vendor_amount_per_invoice,
                                                                                       })

                    else:
                        if user_id_check:
                        # print(total_vendor_amount_per_invoice)
                            existing_record.write(
                                {'released': True, 'user_amount_invoiced': 0.0, 'partial_due_amount': 0.0,
                                 'partial_paid_amount': 0.0,
                                 'user_amount_released': 0.0,'refunded_amount':total_vendor_amount_per_invoice,})
        domain = ['|',('released','=',True),('partial_due_amount','>',0.0),('user_id', '=', self.user_id.id),('user_amount_released','>=',0.0),('bucket_type_id','=',self.user_line_released_bucket_id.bucket_type_id.id)]

        return {
            'name': _('Show In Detail'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'user.invoice.detail',
        }


class VendorLineReleased(models.Model):
    _name = "vendor.line.released.inside.user"

    vendor_id = fields.Many2one('res.partner', 'Vendors')
    vendor_line_released_bucket_id = fields.Many2one('bucket', 'bucket')
    total_amount = fields.Float('Total Amount')

    def fetch_ven_bills_details_inside_user(self):
        print("WORKING")
        fetch_bills = self.env['account.move'].sudo().search([('move_type', '=', "in_invoice")])

        for record in fetch_bills:
            if record.state == 'posted' and record.payment_state in ("paid", "in_payment"):
                if record.invoice_line_ids:
                    amount_paid = 0
                    for move_line_product in record.invoice_line_ids:
                        if len(move_line_product.bucket_ids)>1:
                            for buckets in move_line_product.bucket_ids:
                                if self.vendor_line_released_bucket_id.id == buckets.id:
                                    amount_paid += move_line_product.price_subtotal/len(move_line_product.bucket_ids)
                                    vendor_id = self.env["product.supplierinfo"].sudo().search(
                                        [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                        limit=1,
                                        order="id desc")
                                    existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                        [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                                         ('bucket_type_id', '=', buckets.bucket_type_id.id)])

                                    if not existing_bill_rec:
                                        self.env['vendor.bill.detail'].sudo().create({
                                            'bill_name': record.id,
                                            'vendor_id': vendor_id.partner_id.id,
                                            # 'vendor_amount_bill':move_line_product.price_subtotal,
                                            'vendor_line_released_from_user_bucket_id': self.id,
                                            'vendor_amount_paid': amount_paid,
                                            'bill_paid': True,
                                            'debit': True,
                                            'bucket_type_id': buckets.bucket_type_id.id
                                        })
                                    else:
                                        existing_bill_rec.write({
                                            'vendor_amount_bill': 0.0,
                                            'vendor_line_released_from_user_bucket_id': self.id,
                                            'vendor_amount_paid': amount_paid,
                                            'bill_paid': True,
                                            'debit': True,
                                        })
                        else:

                            if self.vendor_line_released_bucket_id.id == move_line_product.bucket_ids.id:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                    order="id desc")
                                existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                    [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                                     ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                # vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.partner_id.id), (
                                # 'vendor_line_released_bucket_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                if not existing_bill_rec:
                                    self.env['vendor.bill.detail'].sudo().create({
                                        'bill_name': record.id,
                                        'vendor_id': vendor_id.partner_id.id,
                                        # 'vendor_amount_bill':move_line_product.price_subtotal,
                                        'vendor_line_released_from_user_bucket_id': self.id,
                                        'vendor_amount_paid': move_line_product.price_subtotal,
                                        'bill_paid': True,
                                        'debit':True,
                                        'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id
                                    })
                                else:
                                    existing_bill_rec.write({
                                        'vendor_amount_bill': 0.0,
                                        'vendor_amount_paid': move_line_product.price_subtotal,
                                        'bill_paid': True,
                                        'debit': True,
                                    })

                        # existing_bill_rec = self.env['vendor.bill.detail'].sudo().search([('bill_name','=',record.id),('vendor_id','=',self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id)])
                        # if not existing_bill_rec:
                        #     self.env['vendor.bill.detail'].sudo().create({
                        #         'bill_name':record.id,
                        #         'vendor_id':
                        #     })
            if record.state == 'posted' and record.payment_state == 'partial':
                if record.invoice_line_ids:
                    amount_paid = 0
                    amount_bill = 0
                    for move_line_product in record.invoice_line_ids:
                        if len(move_line_product.bucket_ids)>1:
                            for buckets in move_line_product.bucket_ids:

                                if self.vendor_line_released_bucket_id.id == buckets.id :
                                    print(record.id,"PARTIAL BILL PAYMENT")
                                    print(record.id, 'inside Else', self.vendor_line_released_bucket_id.id, buckets.id,
                                          move_line_product.bill_residual_amount)
                                    if move_line_product.bill_residual_amount != 0.0:
                                        amount_bill += move_line_product.price_subtotal / len(
                                            move_line_product.bucket_ids)
                                        amount_paid += (move_line_product.price_subtotal - move_line_product.bill_residual_amount) / len(
                                            move_line_product.bucket_ids)
                                    else:
                                        amount_bill += move_line_product.price_subtotal / len(
                                            move_line_product.bucket_ids)

                                    print(record.id,"ETTTTTTTTTTTTT",amount_bill,amount_paid)
                                    if move_line_product.bill_residual_amount != 0.0:
                                        # amount_bill += move_line_product.price_subtotal / len(
                                        #     move_line_product.bucket_ids)
                                        # amount_paid += (move_line_product.price_subtotal - move_line_product.bill_residual_amount) / len(
                                        #     move_line_product.bucket_ids)
                                        vendor_id = self.env["product.supplierinfo"].sudo().search(
                                            [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                            limit=1,
                                            order="id desc")
                                        existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                            [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                                             ('bucket_type_id', '=', buckets.bucket_type_id.id)])
                                        # vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.partner_id.id), (
                                        #     'vendor_line_released_bucket_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                        if not existing_bill_rec:
                                            self.env['vendor.bill.detail'].sudo().create({
                                                'bill_name': record.id,
                                                'vendor_id': vendor_id.partner_id.id,
                                                'vendor_amount_bill': amount_bill,
                                                'vendor_line_released_from_user_bucket_id': self.id,
                                                'vendor_amount_paid': amount_paid,
                                                'bill_paid': move_line_product.is_bill_paid,
                                                'bucket_type_id': buckets.bucket_type_id.id
                                            })
                                        else:
                                            existing_bill_rec.write({
                                                'vendor_amount_paid': amount_paid,
                                                'bill_paid': move_line_product.is_bill_paid

                                            })
                                    else:
                                        # amount_bill += move_line_product.price_subtotal / len(
                                        #     move_line_product.bucket_ids)
                                        # amount_paid += (move_line_product.price_subtotal - move_line_product.bill_residual_amount) / len(
                                        #     move_line_product.bucket_ids)
                                        print(record.id,"RRRRTTTT",amount_bill,amount_paid)
                                        if move_line_product.bill_residual_amount != 0.0:
                                            print("inside 22222222222")
                                            vendor_id = self.env["product.supplierinfo"].sudo().search(
                                                [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                                limit=1,
                                                order="id desc")
                                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                                [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                                                 ('bucket_type_id', '=', buckets.bucket_type_id.id)])
                                            # vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.partner_id.id),(
                                            #     'vendor_line_released_bucket_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                            if not existing_bill_rec:

                                                self.env['vendor.bill.detail'].sudo().create({
                                                    'bill_name': record.id,
                                                    'vendor_id': vendor_id.partner_id.id,
                                                    'vendor_amount_bill': 0.0,
                                                    'vendor_line_released_from_user_bucket_id': self.id,
                                                    'vendor_amount_paid': move_line_product.price_subtotal/len(move_line_product.bucket_ids),
                                                    'bill_paid': move_line_product.is_bill_paid,
                                                    'bucket_type_id': buckets.bucket_type_id.id
                                                })
                                            else:

                                                existing_bill_rec.write({
                                                    'vendor_amount_paid': (move_line_product.price_subtotal - move_line_product.bill_residual_amount)/len(move_line_product.bucket_ids),
                                                    'vendor_amount_bill': 0.0,
                                                    'bill_paid': move_line_product.is_bill_paid })
                                        else:
                                            print("HERE ELSE")
                                            vendor_id = self.env["product.supplierinfo"].sudo().search(
                                                [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)],
                                                limit=1,
                                                order="id desc")
                                            existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                                [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                                                 ('bucket_type_id', '=', buckets.bucket_type_id.id)])
                                            # vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.partner_id.id),(
                                            #     'vendor_line_released_bucket_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                            if not existing_bill_rec:

                                                self.env['vendor.bill.detail'].sudo().create({
                                                    'bill_name': record.id,
                                                    'vendor_id': vendor_id.partner_id.id,
                                                    'vendor_amount_paid': amount_paid,
                                                    'vendor_line_released_from_user_bucket_id': self.id,
                                                    'vendor_amount_bill': amount_bill,
                                                    'bill_paid': move_line_product.is_bill_paid,
                                                    'bucket_type_id': buckets.bucket_type_id.id
                                                })
                                            else:

                                                existing_bill_rec.write({
                                                    'vendor_amount_bill': amount_bill,
                                                    'vendor_amount_paid': amount_paid,
                                                    'bill_paid': move_line_product.is_bill_paid, })

                        else:
                            if move_line_product.bill_residual_amount != 0.0:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                    order="id desc")
                                existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                    [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                                     ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                # vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.partner_id.id), (
                                #     'vendor_line_released_bucket_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                if not existing_bill_rec:
                                    self.env['vendor.bill.detail'].sudo().create({
                                        'bill_name': record.id,
                                        'vendor_id': vendor_id.partner_id.id,
                                        'vendor_amount_bill': move_line_product.price_subtotal,
                                        'vendor_line_released_from_user_bucket_id': self.id,
                                        'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                        'bill_paid': move_line_product.is_bill_paid,
                                        'bucket_type_id': move_line_product.bucket_ids.bucket_type_id.id
                                    })
                                else:
                                    existing_bill_rec.write({
                                                                'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                                'bill_paid': move_line_product.is_bill_paid

                                    })
                            else:
                                vendor_id = self.env["product.supplierinfo"].sudo().search(
                                    [('product_tmpl_id', '=', move_line_product.product_id.product_tmpl_id.id)], limit=1,
                                    order="id desc")
                                existing_bill_rec = self.env['vendor.bill.detail'].sudo().search(
                                    [('bill_name', '=', record.id), ('vendor_id', '=', vendor_id.partner_id.id),
                                     ('bucket_type_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                # vendor_line_released_id = self.search([('vendor_id', '=', vendor_id.partner_id.id),(
                                #     'vendor_line_released_bucket_id', '=', move_line_product.bucket_ids.bucket_type_id.id)])
                                if not existing_bill_rec:

                                    self.env['vendor.bill.detail'].sudo().create({
                                        'bill_name': record.id,
                                        'vendor_id': vendor_id.partner_id.id,
                                        'vendor_amount_bill': 0.0,
                                        'vendor_line_released_from_user_bucket_id': self.id,
                                        'vendor_amount_paid': move_line_product.price_subtotal,
                                        'bill_paid': move_line_product.is_bill_paid,
                                        'bucket_type_id': self.vendor_line_released_bucket_id.bucket_type_id.id
                                    })
                                else:

                                    existing_bill_rec.write({
                                                                'vendor_amount_paid': move_line_product.price_subtotal - move_line_product.bill_residual_amount,
                                                                'vendor_amount_bill': 0.0,
                                                                'bill_paid': move_line_product.is_bill_paid, })

        domain = [('vendor_id', '=', self.vendor_id.id),('bucket_type_id','=',self.vendor_line_released_bucket_id.bucket_type_id.id)]

        vals = {
            'name': _('Show Bill Detail'),
            'domain': domain,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'target': 'new',
            'res_model': 'vendor.bill.detail',
        }
        return vals