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

    file = fields.Binary(string="CSV File")
    filename = fields.Char(string="Filename")
    line_ids = fields.One2many('bulk.replenishment.line', 'wizard_id', string="Lines")
    step = fields.Selection([('upload', 'Upload CSV'), ('review', 'Review & Confirm')], default='upload')

    def get_product_by_external_id(self, external_id):
        model_data = self.env['ir.model.data'].search([
            '|',
            ('name', '=', external_id),
            ('name', '=', f"__import__.{external_id}")
        ], limit=1)

        if model_data:
            if model_data.model == 'product.product':
                return self.env['product.product'].browse(model_data.res_id)
            elif model_data.model == 'product.template':
                return self.env['product.template'].browse(model_data.res_id).product_variant_id
        return None

    def action_import_csv(self):
        if not self.file:
            raise ValidationError("Please upload a file.")
        self.line_ids.unlink()

        try:
            csv_data = base64.b64decode(self.file)
            data = io.StringIO(csv_data.decode("utf-8"))
            reader = csv.reader(data)
            for row in reader:
                if len(row) < 2:
                    continue
                external_id, quantity = row[0].strip(), row[1].strip()
                product = self.get_product_by_external_id(external_id)
                if not product:
                    continue
                try:
                    quantity = float(quantity)
                except ValueError:
                    continue

                self.env['bulk.replenishment.line'].create({
                    'wizard_id': self.id,
                    'product_id': product.id,
                    'quantity': quantity
                })

            self.step = 'review'

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'bulk.replenishment.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }

        except Exception as e:
            raise ValidationError(f"Error processing file: {str(e)}")

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
    quantity = fields.Float(string="Quantity", required=True)
