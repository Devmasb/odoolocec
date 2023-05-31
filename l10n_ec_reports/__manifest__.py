# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Local - Reportes',
    'version': '14.0.0.0',
    'summary': 'Administración de reportes electrónicos',
    'description': "",
    'author': "Webdit by Jhonatan Saguay",
    'website': 'https://thewebdit.com/',
    'depends': ['base','account'],
    'category': 'Ecuador_Localization',
    'sequence': 13,
    'data': [
        'views/res_config_settings.xml',

        'report/report_einvoice.xml',
        'report/report_withhold.xml',
        'report/edocument_layouts.xml',
        'report/report_enotacredito.xml',
        'report/report_enotadebito.xml',
        'report/report_liqpurchase.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
