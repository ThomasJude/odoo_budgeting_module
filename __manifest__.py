# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'odoo budgeting module',
    'version' : '1.1',
    'summary': 'Budget Module',
    'sequence': 10,
    'description': """
Budget Module
    """,
    'website': 'https://www.oodlestechnologies.com',
    'depends' : ['base', 'product', 'sale','sale_management','purchase','stock'],
    'data': [
        'security/ir.model.access.csv',
        'security/user_group.xml',
        'wizard/vendor_invoice_detail.xml',
        'wizard/vendor_bill_detail.xml',
        'wizard/vendor_bill_item.xml',
        'wizard/user_invoice_detail.xml',
        'wizard/detailed_items.xml',
        'wizard/invoice_bill_wiz_view.xml',
        'wizard/invoice_visibility_wiz_view.xml',
        'wizard/user_invoice_visibility_wiz_view.xml',
        'views/bucket_type_view.xml',
        'views/bucket_view.xml',
        'views/bucket_dashboard_view.xml',
        'views/product_view.xml',
        'views/invoicing.xml',
        'views/allocation_template_view.xml',
        'views/show_vendors.xml',
        'views/partners_view.xml',
        'wizard/bucket_reports_view.xml',
        'views/year_view.xml',
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
