from odoo import fields, api, models, _, tools
import io
import xlwt
import csv
from io import BytesIO
import base64
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from io import StringIO


class BucketReport(models.TransientModel):
    _name = 'bucket.report'

    type = fields.Selection([('weekly','Weekly'),('quarterly','Quarterly'),('monthly','Monthly'),('yearly', 'Yearly')],default='yearly')
    year = fields.Many2one('year','Year')

    @api.onchange('type')
    def onchange_year(self):
        if self.type:
            self.year = ''

    def print_report(self):
        string = 'Bucket Report'
        wb = xlwt.Workbook(encoding='utf-8')
        worksheet = wb.add_sheet(string)
        # worksheet.col(0).width = int(20 * 260)
        # worksheet.col(1).width = int(15 * 260)
        # worksheet.col(2).width = int(20 * 260)
        # worksheet.col(3).width = int(20 * 260)
        # worksheet.col(4).width = int(20 * 260)
        # worksheet.col(5).width = int(20 * 260)
        # worksheet.col(6).width = int(10 * 260)
        # worksheet.col(7).width = int(20 * 260)
        # worksheet.row(0).height_mismatch = True
        # worksheet.row(0).height = 150 * 4
        # worksheet.row(1).height_mismatch = True
        # worksheet.row(1).height = 100 * 4
        # type = capitalize(self.type)
        filename = f"{self.type.capitalize()}" +' '+'Budget Report'+ '.xls'

        style_value = xlwt.easyxf(
            'font: bold on, name Arial ,colour_index black;')
        style_header_cell = xlwt.easyxf(
            'align: horiz center;borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin;', )
        style_header_cell_percent = xlwt.easyxf(
            'align: horiz center;borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin;',num_format_str='0.00' + '%')
        style_header_percent = xlwt.easyxf(
            'align: horiz center;borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin; ' )
        style_header = xlwt.easyxf(
            'align: horiz left;font:bold True;borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin;')
        style_header_i = xlwt.easyxf(
            'align: horiz left;font:italic True;borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin;')
        style_header_add = xlwt.easyxf(
            'align: horiz center;font:bold True;pattern: pattern solid, fore_colour gray25;borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin;')
        style_header_add_left = xlwt.easyxf(
            'align: horiz left;font:bold True;pattern: pattern solid, fore_colour gray25;borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin;')
        format0 = xlwt.easyxf(
            'font:height 500,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        formathead2 = xlwt.easyxf(
            'font:height 250,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        format1 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black,\
                                             left thin, right thin, top thin, bottom thin;')
        format2 = xlwt.easyxf('font:bold True;align: horiz left')
        format3 = xlwt.easyxf('align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black,\
                                             left thin, right thin, top thin, bottom thin;')
        # worksheet.write_merge(0, 0, 0, 3, "Bucket Report", format0)
        # worksheet.write_merge(0, 0, 0, 4, "Date", style_header_add)
        # worksheet.write(1, 0, 'Bucket', style_header_add)
        # worksheet.write(1, 1, 'Actual', style_header_add)
        # worksheet.write(1, 2, 'Budget', style_header_add)
        # worksheet.write(1, 3, 'Remaining', style_header_add)
        # worksheet.write(1, 4, '% Remaining', style_header_add)

        if self.type:
            account_year = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid'))])
            all_date = []
            start_year = ''
            end_year = ''
            for rec_year in account_year:
                all_date.append((str(rec_year.invoice_date)[:4]))
            all_years = sorted(set(all_date))
            a1 = 0
            a2 = 4
            b = 1
            c = 0
            c1 = 1
            c2 = 2
            c3 = 3
            c4 = 4
            if self.type == 'yearly':
                for year in all_years:
                    worksheet.write_merge(0, 0, a1, a2, f"{year}", style_header_add)
                    worksheet.write(b, c, 'Bucket', style_header_add_left)
                    worksheet.write(b, c1, 'Actual', style_header_add)
                    worksheet.write(b, c2, 'Budget', style_header_add)
                    worksheet.write(b, c3, 'Remaining', style_header_add)
                    worksheet.write(b, c4, '% Remaining', style_header_add)
                    b += 1

                    bucket = self.env['bucket'].sudo().search([('bucket_status','=','released')])
                    for rec_bucket in bucket:
                        total_inv_bucket_amount = 0.0
                        total_rel_bucket_amount = 0.0
                        total_bill_bucket_amount = 0.0
                        account_move_out_invoice = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid')),('move_type','=','out_invoice')])
                        account_move_in_invoice = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid')),('move_type','=','in_invoice')])
                        for account_move_rec in account_move_out_invoice:
                            if str(account_move_rec.invoice_date)[:4] == year:
                                for invoice_line in account_move_rec.inv_budget_line:
                                    if invoice_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_inv_bucket_amount += invoice_line.amount
                                for remain_line in account_move_rec.product_remaining_budget_line:
                                    if remain_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_rel_bucket_amount += remain_line.amount
                        for account_bill_rec in account_move_in_invoice:
                            if str(account_bill_rec.invoice_date)[:4] == year:
                                for bill_line in account_bill_rec.invoice_line_ids:
                                    if bill_line.bucket_ids.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_bill_bucket_amount += bill_line.price_subtotal
                        full_bucket_inv_amount = total_inv_bucket_amount + total_rel_bucket_amount
                        full_bucket_bill_amount = total_bill_bucket_amount
                        loss = full_bucket_inv_amount - full_bucket_bill_amount
                        if full_bucket_inv_amount > 0:
                            percent = (loss/full_bucket_inv_amount)
                        else:
                            percent = 0.0

                        worksheet.write(b, c, rec_bucket.name or '',style_header)
                        worksheet.write(b, c1, full_bucket_bill_amount or 0.0,style_header_cell)
                        worksheet.write(b, c2, full_bucket_inv_amount or 0.0,style_header_cell)
                        worksheet.write(b, c3, full_bucket_inv_amount - full_bucket_bill_amount or 0.0,style_header_cell)
                        worksheet.write(b, c4, percent or 0.0,style_header_cell_percent)
                        b += 1
                        sub_bucket = self.env['bucket.type'].sudo().search([('complete_name', 'like', rec_bucket.bucket_type_id.name),('parent_path', 'like', rec_bucket.bucket_type_id.id),
                                                           ('id', '!=', rec_bucket.bucket_type_id.id)])
                        for sub_bucket_rec in sub_bucket:
                            sub_total_rel_bucket_amount = 0.0
                            sub_total_bill_bucket_amount = 0.0
                            account_move_out_invoice = self.env['account.move'].search([('state', '=', 'posted'), ('payment_state', 'in', ('in_payment', 'paid')),('move_type', '=', 'out_invoice')])
                            account_move_in_invoice = self.env['account.move'].search([('state', '=', 'posted'), ('payment_state', 'in', ('in_payment', 'paid')),('move_type', '=', 'in_invoice')])
                            for account_move_rec in account_move_out_invoice:
                                if str(account_move_rec.invoice_date)[:4] == year:
                                    for remain_line in account_move_rec.product_remaining_budget_line:
                                        if remain_line.bucket_type_id.id == rec_bucket.bucket_type_id.id and remain_line.sub_bucket_type.id == sub_bucket_rec.id:
                                            sub_total_rel_bucket_amount += remain_line.amount
                            for account_bill_rec in account_move_in_invoice:
                                if str(account_bill_rec.invoice_date)[:4] == year:
                                    for bill_line in account_bill_rec.invoice_line_ids:
                                        if bill_line.bucket_ids.bucket_type_id.id == rec_bucket.bucket_type_id.id and bill_line.bucket_sub_type.id == sub_bucket_rec.id:
                                            sub_total_bill_bucket_amount += bill_line.price_subtotal
                            loss = sub_total_rel_bucket_amount - sub_total_bill_bucket_amount
                            if sub_total_rel_bucket_amount > 0:
                                percent = (loss / sub_total_rel_bucket_amount)
                            else:
                                percent = 0.0
                            worksheet.write(b, c, sub_bucket_rec.name or '', style_header_i)
                            worksheet.write(b, c1, sub_total_bill_bucket_amount or 0.0, style_header_cell)
                            worksheet.write(b, c2, sub_total_rel_bucket_amount or 0.0, style_header_cell)
                            worksheet.write(b, c3, sub_total_rel_bucket_amount - sub_total_bill_bucket_amount  or 0.0, style_header_cell)
                            worksheet.write(b, c4, percent or 0.0, style_header_cell_percent)
                            b += 1

                    b = 1
                    a1 += 5
                    a2 += 5
                    c += 5
                    c1 += 5
                    c2 += 5
                    c3 += 5
                    c4 += 5

            if self.type == 'monthly':
                final_month = []
                months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
                for month_line in months:
                    month_rec = month_line +'-'+ str(self.year.name)
                    final_month.append(month_rec)

                for final_month_rec in final_month:
                    worksheet.write_merge(0, 0, a1, a2, f"{final_month_rec}", style_header_add)
                    worksheet.write(b, c, 'Bucket', style_header_add_left)
                    worksheet.write(b, c1, 'Actual', style_header_add)
                    worksheet.write(b, c2, 'Budget', style_header_add)
                    worksheet.write(b, c3, 'Remaining', style_header_add)
                    worksheet.write(b, c4, '% Remaining', style_header_add)
                    b += 1

                    bucket = self.env['bucket'].sudo().search([('bucket_status','=','released')])
                    for rec_bucket in bucket:
                        total_inv_bucket_amount = 0.0
                        total_rel_bucket_amount = 0.0
                        total_bill_bucket_amount = 0.0
                        account_move_out_invoice = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid')),('move_type','=','out_invoice')])
                        account_move_in_invoice = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid')),('move_type','=','in_invoice')])
                        for account_move_rec in account_move_out_invoice:
                            if account_move_rec.invoice_date.strftime('%d-%b-%Y').title()[3:] == final_month_rec:
                                for invoice_line in account_move_rec.inv_budget_line:
                                    if invoice_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_inv_bucket_amount += invoice_line.amount
                                for remain_line in account_move_rec.product_remaining_budget_line:
                                    if remain_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_rel_bucket_amount += remain_line.amount
                        for account_bill_rec in account_move_in_invoice:
                            if account_bill_rec.invoice_date.strftime('%d-%b-%Y').title()[3:] == final_month_rec:
                                for bill_line in account_bill_rec.invoice_line_ids:
                                    if bill_line.bucket_ids.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_bill_bucket_amount += bill_line.price_subtotal
                        full_bucket_inv_amount = total_inv_bucket_amount + total_rel_bucket_amount
                        full_bucket_bill_amount = total_bill_bucket_amount
                        loss = full_bucket_inv_amount-full_bucket_bill_amount
                        if full_bucket_inv_amount > 0:
                            percent = (loss/full_bucket_inv_amount)
                        else:
                            percent = 0.0

                        worksheet.write(b, c, rec_bucket.name or '',style_header)
                        worksheet.write(b, c1, full_bucket_bill_amount or 0.0,style_header_cell)
                        worksheet.write(b, c2, full_bucket_inv_amount or 0.0,style_header_cell)
                        worksheet.write(b, c3, full_bucket_inv_amount-full_bucket_bill_amount or 0.0,style_header_cell)
                        worksheet.write(b, c4, percent or 0.0,style_header_cell_percent)
                        b += 1
                        sub_bucket = self.env['bucket.type'].sudo().search([('complete_name', 'like', rec_bucket.bucket_type_id.name),('parent_path', 'like', rec_bucket.bucket_type_id.id),
                                                           ('id', '!=', rec_bucket.bucket_type_id.id)])
                        for sub_bucket_rec in sub_bucket:
                            sub_total_rel_bucket_amount = 0.0
                            sub_total_bill_bucket_amount = 0.0
                            account_move_out_invoice = self.env['account.move'].search([('state', '=', 'posted'), ('payment_state', 'in', ('in_payment', 'paid')),('move_type', '=', 'out_invoice')])
                            account_move_in_invoice = self.env['account.move'].search([('state', '=', 'posted'), ('payment_state', 'in', ('in_payment', 'paid')),('move_type', '=', 'in_invoice')])
                            for account_move_rec in account_move_out_invoice:
                                if account_move_rec.invoice_date.strftime('%d-%b-%Y').title()[3:] == final_month_rec:
                                    for remain_line in account_move_rec.product_remaining_budget_line:
                                        if remain_line.bucket_type_id.id == rec_bucket.bucket_type_id.id and remain_line.sub_bucket_type.id == sub_bucket_rec.id:
                                            sub_total_rel_bucket_amount += remain_line.amount
                            for account_bill_rec in account_move_in_invoice:
                                if account_bill_rec.invoice_date.strftime('%d-%b-%Y').title()[3:] == final_month_rec:
                                    for bill_line in account_bill_rec.invoice_line_ids:
                                        if bill_line.bucket_ids.bucket_type_id.id == rec_bucket.bucket_type_id.id and bill_line.bucket_sub_type.id == sub_bucket_rec.id:
                                            sub_total_bill_bucket_amount += bill_line.price_subtotal
                            loss = sub_total_rel_bucket_amount - sub_total_bill_bucket_amount
                            if sub_total_rel_bucket_amount > 0:
                                percent = (loss / sub_total_rel_bucket_amount)
                            else:
                                percent = 0.0
                            worksheet.write(b, c, sub_bucket_rec.name or '', style_header_i)
                            worksheet.write(b, c1, sub_total_bill_bucket_amount or 0.0, style_header_cell)
                            worksheet.write(b, c2, sub_total_rel_bucket_amount or 0.0, style_header_cell)
                            worksheet.write(b, c3, sub_total_rel_bucket_amount - sub_total_bill_bucket_amount  or 0.0, style_header_cell)
                            worksheet.write(b, c4, percent or 0.0, style_header_cell_percent)
                            b += 1

                    b = 1
                    a1 += 5
                    a2 += 5
                    c += 5
                    c1 += 5
                    c2 += 5
                    c3 += 5
                    c4 += 5

            if self.type == 'quarterly':
                quarters = ['1', '2', '3', '4']

                for quarter_rec in quarters:
                    months = (int(quarter_rec) - 1) * 3 + 1
                    month = int(quarter_rec) * 3
                    print(month,"month")
                    end_quarter = 31 if month in [1, 3, 5, 7, 8, 10,12] else 30 if month != 2 else 29 if int(self.year.name) % 4 == 0 and (
                                int(self.year.name) % 100 != 0 or int(self.year.name) % 400 == 0) else 28

                    final_start = datetime(int(self.year.name),months,1).strftime('%m-%Y')
                    final_end = datetime(int(self.year.name),month,end_quarter).strftime('%m-%Y')
                    quarter_header = str(self.year.name) +'Q'+ quarter_rec
                    worksheet.write_merge(0, 0, a1, a2, f"{quarter_header}", style_header_add)
                    worksheet.write(b, c, 'Bucket', style_header_add_left)
                    worksheet.write(b, c1, 'Actual', style_header_add)
                    worksheet.write(b, c2, 'Budget', style_header_add)
                    worksheet.write(b, c3, 'Remaining', style_header_add)
                    worksheet.write(b, c4, '% Remaining', style_header_add)
                    b += 1

                    bucket = self.env['bucket'].sudo().search([('bucket_status','=','released')])
                    for rec_bucket in bucket:
                        total_inv_bucket_amount = 0.0
                        total_rel_bucket_amount = 0.0
                        total_bill_bucket_amount = 0.0
                        account_move_out_invoice = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid')),('move_type','=','out_invoice')])
                        account_move_in_invoice = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid')),('move_type','=','in_invoice')])
                        for account_move_rec in account_move_out_invoice:
                            print(final_start)
                            print(final_end)
                            print(account_move_rec.invoice_date.strftime('%d-%m-%Y')[3:],"exist")
                            if final_start <= account_move_rec.invoice_date.strftime('%d-%m-%Y')[3:] <= final_end:
                            # if account_move_rec.invoice_date.strftime('%d-%b-%Y').title()[3:] == final_month_rec:
                                for invoice_line in account_move_rec.inv_budget_line:
                                    if invoice_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_inv_bucket_amount += invoice_line.amount
                                for remain_line in account_move_rec.product_remaining_budget_line:
                                    if remain_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_rel_bucket_amount += remain_line.amount
                        for account_bill_rec in account_move_in_invoice:
                            if final_start <= account_bill_rec.invoice_date.strftime('%d-%m-%Y')[3:] <= final_end:
                                for bill_line in account_bill_rec.invoice_line_ids:
                                    if bill_line.bucket_ids.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_bill_bucket_amount += bill_line.price_subtotal
                        full_bucket_inv_amount = total_inv_bucket_amount + total_rel_bucket_amount
                        full_bucket_bill_amount = total_bill_bucket_amount
                        loss = full_bucket_inv_amount - full_bucket_bill_amount
                        if full_bucket_inv_amount > 0:
                            percent = (loss/full_bucket_inv_amount)
                        else:
                            percent = 0.0

                        worksheet.write(b, c, rec_bucket.name or '',style_header)
                        worksheet.write(b, c1, full_bucket_bill_amount or 0.0,style_header_cell)
                        worksheet.write(b, c2, full_bucket_inv_amount or 0.0,style_header_cell)
                        worksheet.write(b, c3, full_bucket_inv_amount - full_bucket_bill_amount or 0.0,style_header_cell)
                        worksheet.write(b, c4, percent or 0.0,style_header_cell_percent)
                        b += 1
                        sub_bucket = self.env['bucket.type'].sudo().search([('complete_name', 'like', rec_bucket.bucket_type_id.name),('parent_path', 'like', rec_bucket.bucket_type_id.id),
                                                           ('id', '!=', rec_bucket.bucket_type_id.id)])
                        for sub_bucket_rec in sub_bucket:
                            sub_total_rel_bucket_amount = 0.0
                            sub_total_bill_bucket_amount = 0.0
                            account_move_out_invoice = self.env['account.move'].search([('state', '=', 'posted'), ('payment_state', 'in', ('in_payment', 'paid')),('move_type', '=', 'out_invoice')])
                            account_move_in_invoice = self.env['account.move'].search([('state', '=', 'posted'), ('payment_state', 'in', ('in_payment', 'paid')),('move_type', '=', 'in_invoice')])
                            for account_move_rec in account_move_out_invoice:
                                if final_start <= account_move_rec.invoice_date.strftime('%d-%m-%Y')[3:] <= final_end:
                                    for remain_line in account_move_rec.product_remaining_budget_line:
                                        if remain_line.bucket_type_id.id == rec_bucket.bucket_type_id.id and remain_line.sub_bucket_type.id == sub_bucket_rec.id:
                                            sub_total_rel_bucket_amount += remain_line.amount
                            for account_bill_rec in account_move_in_invoice:
                                if final_start <= account_bill_rec.invoice_date.strftime('%d-%m-%Y')[3:] <= final_end:
                                    for bill_line in account_bill_rec.invoice_line_ids:
                                        if bill_line.bucket_ids.bucket_type_id.id == rec_bucket.bucket_type_id.id and bill_line.bucket_sub_type.id == sub_bucket_rec.id:
                                            sub_total_bill_bucket_amount += bill_line.price_subtotal
                            loss = sub_total_rel_bucket_amount - sub_total_bill_bucket_amount
                            if sub_total_rel_bucket_amount > 0:
                                percent = (loss / sub_total_rel_bucket_amount)
                            else:
                                percent = 0.0
                            worksheet.write(b, c, sub_bucket_rec.name or '', style_header_i)
                            worksheet.write(b, c1, sub_total_bill_bucket_amount or 0.0, style_header_cell)
                            worksheet.write(b, c2, sub_total_rel_bucket_amount or 0.0, style_header_cell)
                            worksheet.write(b, c3, sub_total_rel_bucket_amount - sub_total_bill_bucket_amount  or 0.0, style_header_cell)
                            worksheet.write(b, c4, percent or 0.0, style_header_cell_percent)
                            b += 1
                    b = 1
                    a1 += 5
                    a2 += 5
                    c += 5
                    c1 += 5
                    c2 += 5
                    c3 += 5
                    c4 += 5

            if self.type == 'weekly':
                weeks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
                         30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

                for week_rec in weeks:
                    base_date = datetime(int(self.year.name), 1, 4)
                    offset = timedelta(days=(week_rec - 1) * 7)
                    first_date = base_date - timedelta(days=base_date.weekday()) + offset
                    last_date = first_date + timedelta(days=6)
                    final_start = first_date.strftime('%Y,%m,%d')
                    final_end = last_date.strftime('%Y,%m,%d')
                    final_header = str(self.year.name) + 'W'+ str(week_rec)
                    worksheet.write_merge(0, 0, a1, a2, f"{final_header}", style_header_add)
                    worksheet.write(b, c, 'Bucket', style_header_add_left)
                    worksheet.write(b, c1, 'Actual', style_header_add)
                    worksheet.write(b, c2, 'Budget', style_header_add)
                    worksheet.write(b, c3, 'Remaining', style_header_add)
                    worksheet.write(b, c4, '% Remaining', style_header_add)
                    b += 1

                    bucket = self.env['bucket'].sudo().search([('bucket_status','=','released')])
                    for rec_bucket in bucket:
                        total_inv_bucket_amount = 0.0
                        total_rel_bucket_amount = 0.0
                        total_bill_bucket_amount = 0.0
                        account_move_out_invoice = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid')),('move_type','=','out_invoice')])
                        account_move_in_invoice = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid')),('move_type','=','in_invoice')])
                        for account_move_rec in account_move_out_invoice:

                            if str(final_start) <= str(account_move_rec.invoice_date.strftime('%Y,%m,%d')) <= str(final_end):
                                print("if")
                            # if account_move_rec.invoice_date.strftime('%d-%b-%Y').title()[3:] == final_month_rec:
                                for invoice_line in account_move_rec.inv_budget_line:
                                    if invoice_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_inv_bucket_amount += invoice_line.amount
                                for remain_line in account_move_rec.product_remaining_budget_line:
                                    if remain_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_rel_bucket_amount += remain_line.amount
                        for account_bill_rec in account_move_in_invoice:
                            if str(final_start) <= str(account_bill_rec.invoice_date.strftime('%Y,%m,%d')) <= str(final_end):
                                for bill_line in account_bill_rec.invoice_line_ids:
                                    if bill_line.bucket_ids.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_bill_bucket_amount += bill_line.price_subtotal
                        full_bucket_inv_amount = total_inv_bucket_amount + total_rel_bucket_amount
                        full_bucket_bill_amount = total_bill_bucket_amount
                        loss = full_bucket_inv_amount - full_bucket_bill_amount
                        if full_bucket_inv_amount > 0:
                            percent = (loss/full_bucket_inv_amount)
                        else:
                            percent = 0.0

                        worksheet.write(b, c, rec_bucket.name or '',style_header)
                        worksheet.write(b, c1, full_bucket_bill_amount or 0.0,style_header_cell)
                        worksheet.write(b, c2, full_bucket_inv_amount or 0.0,style_header_cell)
                        worksheet.write(b, c3, full_bucket_inv_amount - full_bucket_bill_amount or 0.0,style_header_cell)
                        worksheet.write(b, c4, percent or 0.0,style_header_cell_percent)
                        b += 1
                        sub_bucket = self.env['bucket.type'].sudo().search([('complete_name', 'like', rec_bucket.bucket_type_id.name),('parent_path', 'like', rec_bucket.bucket_type_id.id),
                                                           ('id', '!=', rec_bucket.bucket_type_id.id)])
                        for sub_bucket_rec in sub_bucket:
                            sub_total_rel_bucket_amount = 0.0
                            sub_total_bill_bucket_amount = 0.0
                            account_move_out_invoice = self.env['account.move'].search([('state', '=', 'posted'), ('payment_state', 'in', ('in_payment', 'paid')),('move_type', '=', 'out_invoice')])
                            account_move_in_invoice = self.env['account.move'].search([('state', '=', 'posted'), ('payment_state', 'in', ('in_payment', 'paid')),('move_type', '=', 'in_invoice')])
                            for account_move_rec in account_move_out_invoice:
                                if str(final_start) <= account_move_rec.invoice_date.strftime('%Y,%m,%d') <= str(final_end):
                                    for remain_line in account_move_rec.product_remaining_budget_line:
                                        if remain_line.bucket_type_id.id == rec_bucket.bucket_type_id.id and remain_line.sub_bucket_type.id == sub_bucket_rec.id:
                                            sub_total_rel_bucket_amount += remain_line.amount
                            for account_bill_rec in account_move_in_invoice:
                                if str(final_start) <= account_bill_rec.invoice_date.strftime('%Y,%m,%d') <= str(final_end):
                                    for bill_line in account_bill_rec.invoice_line_ids:
                                        if bill_line.bucket_ids.bucket_type_id.id == rec_bucket.bucket_type_id.id and bill_line.bucket_sub_type.id == sub_bucket_rec.id:
                                            sub_total_bill_bucket_amount += bill_line.price_subtotal
                            loss = sub_total_rel_bucket_amount - sub_total_bill_bucket_amount
                            if sub_total_rel_bucket_amount > 0:
                                percent = (loss / sub_total_rel_bucket_amount)
                            else:
                                percent = 0.0
                            worksheet.write(b, c, sub_bucket_rec.name or '', style_header_i)
                            worksheet.write(b, c1, sub_total_bill_bucket_amount or 0.0, style_header_cell)
                            worksheet.write(b, c2, sub_total_rel_bucket_amount or 0.0, style_header_cell)
                            worksheet.write(b, c3, sub_total_rel_bucket_amount - sub_total_bill_bucket_amount  or 0.0, style_header_cell)
                            worksheet.write(b, c4, percent or 0.0, style_header_cell_percent)
                            b += 1

                    b = 1
                    a1 += 5
                    a2 += 5
                    c += 5
                    c1 += 5
                    c2 += 5
                    c3 += 5
                    c4 += 5

        fp = io.BytesIO()
        wb.save(fp)
        out = base64.encodebytes(fp.getvalue())
        view_report_status_id = self.env['bucket.view.report'].create({'excel_file': out, 'file_name': filename})
        return {
            'res_id': view_report_status_id.id,
            'name': 'Report',
            'view_mode': 'form',
            'res_model': 'bucket.view.report',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

class bucket_view_report(models.TransientModel):
    _name = 'bucket.view.report'
    _rec_name = 'excel_file'

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)
