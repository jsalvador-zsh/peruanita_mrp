from odoo import models, fields, api
from collections import defaultdict

class MrpConsolidation(models.Model):
    _name = 'mrp.consolidation'
    _description = 'Consolidación de Órdenes de Producción'
    _order = 'create_date desc'

    name = fields.Char('Nombre', required=True, default='Nueva Consolidación')
    production_ids = fields.Many2many('mrp.production', string='Órdenes de Producción')
    consolidation_line_ids = fields.One2many('mrp.consolidation.line', 'consolidation_id', string='Líneas Consolidadas')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('calculated', 'Calculado'),
        ('confirmed', 'Confirmado'),
    ], default='draft', string='Estado')
    total_products = fields.Integer('Total Productos Finales', compute='_compute_totals')
    total_components = fields.Integer('Total Componentes', compute='_compute_totals')
    
    @api.depends('consolidation_line_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_products = len(rec.production_ids)
            rec.total_components = len(rec.consolidation_line_ids)

    def calculate_consolidation(self):
        """Calcula la consolidación de materiales"""
        self.consolidation_line_ids.unlink()  # Limpiar líneas anteriores
        
        consolidated_materials = defaultdict(float)
        
        # Recorrer todas las órdenes de producción seleccionadas
        for production in self.production_ids:
            if production.state not in ['draft', 'confirmed', 'progress']:
                continue
                
            # Recorrer los movimientos de materiales de cada orden
            for move in production.move_raw_ids:
                if move.state == 'cancel':
                    continue
                    
                product_key = move.product_id.id
                consolidated_materials[product_key] += move.product_uom_qty
        
        # Crear las líneas consolidadas
        for product_id, qty_needed in consolidated_materials.items():
            product = self.env['product.product'].browse(product_id)
            
            self.env['mrp.consolidation.line'].create({
                'consolidation_id': self.id,
                'product_id': product_id,
                'qty_needed': qty_needed,
                'uom_id': product.uom_id.id,
                'qty_available': product.qty_available,
                'qty_forecasted': product.virtual_available,
            })
        
        self.state = 'calculated'

    def confirm_consolidation(self):
        """Confirma la consolidación"""
        self.state = 'confirmed'

    def create_purchase_suggestion(self):
        """Crea sugerencias de compra para productos faltantes"""
        purchase_lines = []
        
        for line in self.consolidation_line_ids:
            if line.qty_missing > 0:
                # Buscar el proveedor principal del producto
                supplier = line.product_id.seller_ids[:1]
                if supplier:
                    purchase_lines.append({
                        'product_id': line.product_id.id,
                        'product_qty': line.qty_missing,
                        'price_unit': supplier.price,
                        'partner_id': supplier.partner_id.id,
                    })
        
        if purchase_lines:
            # Crear wizard o vista para mostrar sugerencias
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sugerencias de Compra',
                'res_model': 'mrp.purchase.suggestion',
                'view_mode': 'list',
                'target': 'new',
                'context': {'default_purchase_lines': purchase_lines}
            }


class MrpConsolidationLine(models.Model):
    _name = 'mrp.consolidation.line'
    _description = 'Línea de Consolidación'

    consolidation_id = fields.Many2one('mrp.consolidation', string='Consolidación')
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    qty_needed = fields.Float('Cantidad Necesaria', digits='Product Unit of Measure')
    qty_available = fields.Float('Stock Disponible', digits='Product Unit of Measure')
    qty_forecasted = fields.Float('Stock Proyectado', digits='Product Unit of Measure')
    qty_missing = fields.Float('Cantidad Faltante', compute='_compute_qty_missing', digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unidad de Medida')
    category_id = fields.Many2one('product.category', related='product_id.categ_id', string='Categoría')
    supplier_id = fields.Many2one('res.partner', compute='_compute_supplier', string='Proveedor Principal')
    
    @api.depends('qty_needed', 'qty_available')
    def _compute_qty_missing(self):
        for line in self:
            line.qty_missing = max(0, line.qty_needed - line.qty_available)
    
    @api.depends('product_id')
    def _compute_supplier(self):
        for line in self:
            supplier = line.product_id.seller_ids[:1]
            line.supplier_id = supplier.partner_id.id if supplier else False