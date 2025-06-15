from odoo import models, fields, api

class InventoryByRouteWizard(models.TransientModel):
    _name = 'inventory.by.route.wizard'
    _description = 'Inventory by route wizard'

    state = fields.Selection([
        ('select_route', 'Select Route'),
        ('adjust_stock', 'Show Stock')
    ], default='select_route')

    route_id = fields.Many2one(
        'stock.location.route',
        string='Supplier',
        required=True,
        domain="[('product_selectable', '=', True), ('name', 'not in', ['Buy'])]"
    )

    product_lines = fields.One2many('inventory.by.route.line', 'wizard_id', string='Products')

    def action_next(self):
        # Get products with selected route
        products = self.env['product.product'].search([('route_ids', 'in', self.route_id.id)])
        stock_location = self.env.ref('stock.stock_location_stock')  # WH/Stock

        if not products:
            raise UserError("No products found for the specified supplier (route).")

        lines = []
        for product in products:
            qty = product.with_context({'location': stock_location.id}).qty_available
            lines.append((0, 0, {
                'product_id': product.id,
                'quantity': qty,
                'new_quantity': qty,
            }))
        self.product_lines = lines
        self.state = 'adjust_stock'
        return {
            'type': 'ir.actions.act_window',
            'name': f"Step 2: Review & Adjust Stock ({self.route_id.name or ''})",
            'res_model': 'inventory.by.route.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_apply_stock_adjustment(self):
        """Adjust stock only for lines with a non-empty new_quantity."""
        stock_location = self.env.ref('stock.stock_location_stock')
        lines_to_update = self.product_lines.filtered(lambda l: l.new_quantity not in (False, None))

        if not lines_to_update:
            raise UserError("No stock quantities were entered to update.")

        for line in lines_to_update:
            rounding = line.product_id.uom_id.rounding or 0.01
            if abs(line.new_quantity - line.quantity) > rounding:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', stock_location.id)
                ], limit=1)

                quant.inventory_quantity = line.new_quantity
                quant._apply_inventory()

        return {'type': 'ir.actions.act_window_close'}

class InventoryByRouteLine(models.TransientModel):
    _name = 'inventory.by.route.line'
    _description = 'Inventory By Route Line'

    wizard_id = fields.Many2one('inventory.by.route.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Current Stock', readonly=True)
    new_quantity = fields.Float(string='Adjust Stock', default=False)
