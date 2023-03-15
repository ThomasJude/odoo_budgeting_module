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
    'depends' : ['base', 'product', 'sale','sale_management','purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_view.xml',
        
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
