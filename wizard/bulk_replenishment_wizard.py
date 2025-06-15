import base64
import csv
import io
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class BulkReplenishmentWizard(models.TransientModel):
    _name = 'bulk.replenishment.wizard'
    _description = 'Bulk Inventory Replenishment Wizard'

    state = fields.Selection([
        ('select_route', 'Select Supplier'),
        ('replenish', 'Confirm')
    ], default='select_route')

    route_id = fields.Many2one(
        'stock.location.route',
        string='Supplier',
        required=True,
        domain="[('product_selectable', '=', True), ('name', 'not in', ['Buy'])]"
    )

    line_ids = fields.One2many('bulk.replenishment.line', 'wizard_id', string="Lines")

    def action_next(self):
        # Get products with selected route
        products = self.env['product.product'].search([('route_ids', 'in', self.route_id.id)])

        for product in products:
            self.env['bulk.replenishment.line'].create({
                'wizard_id': self.id,
                'product_id': product.id,
                'quantity': 0
            })

        self.state = 'replenish'

        return {
            'type': 'ir.actions.act_window',
            'name': f"Step 2: Replenish Stock ({self.route_id.name or ''})",
            'res_model': 'bulk.replenishment.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_process_lines(self):
        stock_location = self.env.ref('stock.stock_location_stock')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        picking_type = self.env.ref('stock.picking_type_in')

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': supplier_location.id,
            'location_dest_id': stock_location.id,
            'move_type': 'direct',
        })

        for line in self.line_ids:
            if line.quantity == 0:
                continue

            self.env['stock.move'].create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': supplier_location.id,
                'location_dest_id': stock_location.id,
            })

        picking.action_confirm()
        for move in picking.move_ids_without_package:
            move.quantity_done = move.product_uom_qty
        picking.button_validate()

        return {'type': 'ir.actions.act_window_close'}

class BulkReplenishmentLine(models.TransientModel):
    _name = 'bulk.replenishment.line'
    _description = 'Bulk Replenishment Line'

    wizard_id = fields.Many2one('bulk.replenishment.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity = fields.Float(string="Quantity Received", required=True)
