# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ec_code_base = fields.Char(string='Code base', help='Tax declaration code of the base amount prior to the calculation of the tax')
    l10n_ec_code_applied = fields.Char(string='Code applied', help='Tax declaration code of the resulting amount after the calculation of the tax')
    l10n_ec_code_ats = fields.Char(string='Code ATS', help='Tax Identification Code for the Simplified Transactional Annex')
    # l10n_ec_type = fields.Selection(related='tax_group_id.l10n_ec_type')
    l10n_ec_sri_code = fields.Char(string='Code SRI', help='Tax Identification Code for SRI Document')

class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'    

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)        
        vals.update({
            'l10n_ec_code_base': self.l10n_ec_code_base,
            'l10n_ec_code_applied': self.l10n_ec_code_applied,
            'l10n_ec_code_ats': self.l10n_ec_code_ats,
            'l10n_ec_sri_code':self.l10n_ec_sri_code,
        })
        return vals
    
    l10n_ec_code_base = fields.Char(string='Code base', help='Tax declaration code of the base amount prior to the calculation of the tax')
    l10n_ec_code_applied = fields.Char(string='Code applied', help='Tax declaration code of the resulting amount after the calculation of the tax')
    l10n_ec_code_ats = fields.Char(string='Code ATS', help='Tax Identification Code for the Simplified Transactional Annex')
    l10n_ec_sri_code = fields.Char(string='Code SRI', help='Tax Identification Code for SRI Document')