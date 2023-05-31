from odoo import fields, models, api


class SriAuthorization(models.Model):
    _name = 'sri.authorization'
    _description = 'SRI Authorization'

    sri_authorization_code = fields.Char()
    sri_create_date = fields.Datetime()
    sri_authorization_date = fields.Char()


    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    processed = fields.Boolean(default=False)
    env_service = fields.Selection(
        [
            ('1', 'Test'),
            ('2', 'Production')
        ],
        string='Environment Type',
        required=True,
        )

    account_move = fields.Many2one('account.move', string='Invoice Related')

    error_code = fields.Selection(
        [
            ('2', 'RUC del emisor NO se encuentra ACTIVO'),
            ('2', 'Production')
        ],
        string='Environment Type',
        required=False,
    )
    authorization_type = fields.Selection(
		[("guide", "guide"),
		 ("move", "move"),
         ("withhold","withhold")],
		string="Authorization Type"
	)

    def name_get(self):
        result = []
        for record in self:
            name = record.sri_authorization_code
            result.append((record.id, name))
        return result

    


