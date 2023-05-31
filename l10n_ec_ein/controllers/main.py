from odoo import http
from odoo.http import request
from odoo.addons.account.controllers.portal import PortalAccount
import logging
_logger = logging.getLogger(__name__)

class PortalAccountInherit(PortalAccount):
    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        type_document=invoice_sudo.l10n_latam_document_type_id
        report_ref='account.account_invoices'
        if type_document:
            if type_document.code=='01':
                #factura
                report_ref='l10n_ec_reports.account_invoices_elec'
            elif type_document.code=='04':
                #nota de credito
                report_ref='l10n_ec_reports.account_creditnote_elec'
            elif type_document.code=='05':
                #nota de debito
                report_ref='l10n_ec_reports.account_debitnote_elec'
            
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=invoice_sudo, report_type=report_type, report_ref=report_ref, download=download)

        values = self._invoice_get_page_view_values(invoice_sudo, access_token, **kw)
        acquirers = values.get('acquirers')
        if acquirers:
            country_id = values.get('partner_id') and values.get('partner_id')[0].country_id.id
            values['acq_extra_fees'] = acquirers.get_acquirer_extra_fees(invoice_sudo.amount_residual, invoice_sudo.currency_id, country_id)

        return request.render("account.portal_invoice_page", values)