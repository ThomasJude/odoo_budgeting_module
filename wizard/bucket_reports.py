from odoo import fields, api, models, _, tools
import io
import xlwt
import csv
from io import BytesIO
import base64
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from xlsxwriter.workbook import Workbook
from io import StringIO


class BucketReport(models.TransientModel):
    _name = 'bucket.report'

    type = fields.Selection([('week','Weekly'),('quarter','Quarterly'),('month','Monthly'),('yearly', 'Yearly')],default='yearly')

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
        filename = 'Bucket Report' + '.xls'
        style_value = xlwt.easyxf(
            'font: bold on, name Arial ,colour_index black;')
        style_header = xlwt.easyxf(
            'font: height 280, name Arial, colour_index black, bold on, italic off; align: wrap on, vert centre, horiz center;')
        style_header_add = xlwt.easyxf(
            'align: horiz center;font:bold True;borders: top_color black, bottom_color black, right_color black, left_color black,left thin, right thin, top thin, bottom thin;')
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
            print(all_years,"all date")
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
                    print(a1,a2,"a1 a2")
                    worksheet.write_merge(0, 0, a1, a2, f"{year}", style_header_add)
                    worksheet.write(b, c, 'Bucket', style_header_add)
                    worksheet.write(b, c1, 'Actual', style_header_add)
                    worksheet.write(b, c2, 'Budget', style_header_add)
                    worksheet.write(b, c3, 'Remaining', style_header_add)
                    worksheet.write(b, c4, '% Remaining', style_header_add)
                    b += 1

                    bucket = self.env['bucket'].sudo().search([('bucket_status','=','released')])
                    for rec_bucket in bucket:
                        full_bucket_inv_amount = 0.0
                        full_bucket_rel_amount = 0.0
                        total_inv_bucket_amount = 0.0
                        total_rel_bucket_amount = 0.0
                        account_move = self.env['account.move'].search([('state','=','posted'),('payment_state','in',('in_payment','paid')),('move_type','=','out_invoice')])
                        for account_move_rec in account_move:
                            if str(account_move_rec.invoice_date)[:4] == year:
                                for invoice_line in account_move_rec.inv_budget_line:
                                    if invoice_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_inv_bucket_amount += invoice_line.amount
                                for remain_line in account_move_rec.product_remaining_budget_line:
                                    if remain_line.bucket_type_id.id == rec_bucket.bucket_type_id.id:
                                        total_rel_bucket_amount += remain_line.amount
                        full_bucket_inv_amount = total_inv_bucket_amount + total_rel_bucket_amount
                        loss = full_bucket_rel_amount - full_bucket_inv_amount
                        if full_bucket_rel_amount > 0:
                            percent = (loss/full_bucket_rel_amount) * 100
                        else:
                            percent = 0.0

                        worksheet.write(b, c, rec_bucket.name or '')
                        worksheet.write(b, c1, full_bucket_rel_amount or 0.0)
                        worksheet.write(b, c2, full_bucket_inv_amount or 0.0)
                        worksheet.write(b, c3, full_bucket_rel_amount-full_bucket_inv_amount or 0.0)
                        worksheet.write(b, c4, percent or 0.0)
                        b += 1
                    b = 1
                    a1 += 5
                    a2 += 5
                    c += 5
                    c1 += 5
                    c2 += 5
                    c3 += 5
                    c4 += 5



        #
        # a = 2
        # if self.client_wise:
        #     record = self.env['account.move'].sudo().search(
        #         [('partner_id', '=', self.client_wise.id), ('move_type', '=', 'out_invoice')])
        #     if record:
        #         for rec in record:
        #             worksheet.write(a, 0, rec.partner_id.name or '')
        #             worksheet.write(a, 1, rec.name or '')
        #             for vals_line in rec.invoice_line_ids:
        #                 worksheet.write(a, 2, vals_line.product_id.name or '')
        #                 worksheet.write(a, 3, vals_line.price_subtotal or '')
        #                 a += 1
        #             a += 1

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