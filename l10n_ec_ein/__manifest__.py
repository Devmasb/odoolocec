# -*- coding: utf-8 -*-
{
    'name': "Ecuador Electronic Invoice",

    'summary': """
                This is a contribution to localize odoo in Ecuador
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Webdit by Jhonatan Saguay",
    'website': "https://thewebdit.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Ecuador_Localization',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'account',
                'l10n_ec_account',
                'l10n_ec_par',
                'l10n_ec_seq',
                'l10n_ec_reports',
                'purchase',
                'sh_message',
                'account_debit_note',
                'account_invoice_refund_link',

                ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/sri_authorization_security.xml',
        # 'data/data.xml',
        # 'data/code_sri_date.xml',
        # 'data/res_bank_data.xml',
        'data/move_cron.xml',
        'views/sri_authorization.xml',
        'views/invoice_view.xml',
        # 'views/sri_error_code.xml',
        'views/account_journal.xml',
        'views/account_move.xml',
        # 'views/sri_parameters.xml',
        # 'views/sri_tax_code.xml',
        # 'views/tax.xml',
        'views/sri_sign.xml',
        'edi/einvoice_edi.xml',
        'edi/edebitnote.xml',
        'edi/ecreditnote.xml',
        'edi/eliqpruchase.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
