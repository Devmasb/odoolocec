# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    _TYPE_EC = [
        ('vat12', 'VAT 12%'),
        ('vat14', 'VAT 14%'),
        ('zero_vat', 'VAT 0%'),
        ('not_charged_vat', 'VAT Not Charged'),
        ('exempt_vat', 'VAT Excempt'),
        ('withhold_vat', 'VAT Withhold'),
        ('withhold_income_tax', 'Profit Withhold'),
        ('ice', 'Special Consumptions Tax (ICE)'),
        ('irbpnr', 'Plastic Bottles (IRBPNR)'),
        ('outflows_tax', 'Exchange Outflows'),
        ('other', 'Others'),
        ('ret_vat_b10', 'Vat Withhold 10%'),
        ('ret_vat_srv20', 'Vat Withhold 20%'),
        ('ret_vat_b30', 'Vat Withhold 30%'),
        ('ret_vat_srv50', 'Vat Withhold 50%'),
        ('ret_vat_srv70', 'Vat Withhold 70%'),
        ('ret_vat_srv100', 'Vat Withhold 100%'),
        ('ret_ir', 'Rent Withhold'),
        
    ]
    _TAX_CAT = [
        ('1','RENT'),
        ('2','IVA'),
        ('3','ICE'),
    ]
    
    l10n_ec_type = fields.Selection(_TYPE_EC, string='Type Ecuadorian Tax', track_visibility='onchange',
                                    help='Ecuadorian taxes subtype')
    code = fields.Selection(_TAX_CAT, string='Category Tax',
                                    help='Category Ecuadorian Tax')
