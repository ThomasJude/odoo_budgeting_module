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
        'wizard/vendor_invoice_detail.xml',
        'wizard/user_invoice_detail.xml',
        'views/bucket_type_view.xml',
        'views/bucket_view.xml',
        'views/bucket_dashboard_view.xml',
        'views/product_view.xml',
        'views/invoicing.xml',
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
