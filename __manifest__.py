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
        'views/bucket_type_view.xml',
        # 'security/salesforce_connector_security.xml',
        # 'data/data_crm_stage.xml',
        # 'data/email_template.xml',
        # 'wizard/message_wizard.xml',
        'views/product_view.xml',
        # 'views/sale_contract_view.xml',
        # 'views/lead_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
