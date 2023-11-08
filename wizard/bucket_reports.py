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
        worksheet.col(0).width = int(20 * 260)
        worksheet.col(1).width = int(15 * 260)
        worksheet.col(2).width = int(20 * 260)
        worksheet.col(3).width = int(20 * 260)
        worksheet.col(4).width = int(20 * 260)
        worksheet.col(5).width = int(20 * 260)
        worksheet.col(6).width = int(10 * 260)
        worksheet.col(7).width = int(20 * 260)
        worksheet.row(0).height_mismatch = True
        worksheet.row(0).height = 150 * 4
        worksheet.row(1).height_mismatch = True
        worksheet.row(1).height = 100 * 4
        filename = 'Bucket Report' + '.xls'
        style_value = xlwt.easyxf(
            'font: bold on, name Arial ,colour_index black;')
        style_header = xlwt.easyxf(
            'font: height 280, name Arial, colour_index black, bold on, italic off; align: wrap on, vert centre, horiz center;')
        format0 = xlwt.easyxf(
            'font:height 500,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        formathead2 = xlwt.easyxf(
            'font:height 250,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        format1 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black,\
                                             left thin, right thin, top thin, bottom thin;')
        format2 = xlwt.easyxf('font:bold True;align: horiz left')
        format3 = xlwt.easyxf('align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black,\
                                             left thin, right thin, top thin, bottom thin;')
        worksheet.write_merge(0, 0, 0, 3, "Bucket Report", format0)
        worksheet.write_merge(1, 1, 0, 3, "Date", formathead2)
        worksheet.write(2, 0, 'Bucket Name', format1)
        worksheet.write(2, 1, 'Actual', format1)
        worksheet.write(2, 2, 'Product', format1)
        worksheet.write(2, 3, 'Total Amount', format1)

        a = 3
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