from odoo import models, fields, api

class InventoryByRouteWizard(models.TransientModel):
    _name = 'inventory.by.route.wizard'
    _description = 'Inventory by route wizard'

    state = fields.Selection([
        ('select_route', 'Select Route'),
        ('show_stock', 'Show Stock')
    ], default='select_route')

    route_id = fields.Many2one(
        'stock.location.route',
        string='Supplier',
        required=True,
        domain="[('product_selectable', '=', True), ('name', 'not in', ['Buy'])]"
    )

    product_lines = fields.One2many('inventory.by.route.line', 'wizard_id', string='Products', readonly=True)

    def action_next(self):
        # Get products with selected route
        products = self.env['product.product'].search([('route_ids', 'in', self.route_id.id)])
        stock_location = self.env.ref('stock.stock_location_stock')  # WH/Stock

        lines = []
        for product in products:
            qty = product.with_context({'location': stock_location.id}).qty_available
            lines.append((0, 0, {
                'product_id': product.id,
                'quantity': qty,
            }))
        self.product_lines = lines
        self.state = 'show_stock'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'inventory.by.route.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

class InventoryByRouteLine(models.TransientModel):
    _name = 'inventory.by.route.line'
    _description = 'Inventory By Route Line'

    wizard_id = fields.Many2one('inventory.by.route.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Stock Quantity')
