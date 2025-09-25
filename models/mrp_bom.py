from odoo import models, fields, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    
    waste_percentage = fields.Float(
        string='Porcentaje de Merma (%)',
        default=0.0,
        help="Porcentaje de merma que se aplicará a todos los componentes de esta BOM. "
             "Ejemplo: 5.0 para 5% de merma adicional"
    )
    
    @api.onchange('waste_percentage')
    def _onchange_waste_percentage(self):
        """Recalcula las mermas cuando cambia el porcentaje"""
        if self.bom_line_ids:
            for line in self.bom_line_ids:
                line._compute_waste_qty()


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'
    
    waste_qty = fields.Float(
        string='Cantidad Merma',
        compute='_compute_waste_qty',
        store=True,
        digits='Product Unit of Measure',
        help="Cantidad de merma calculada basada en el porcentaje de merma del BOM"
    )
    
    total_qty_with_waste = fields.Float(
        string='Cantidad Total (con Merma)',
        compute='_compute_total_qty_with_waste',
        store=True,
        digits='Product Unit of Measure',
        help="Cantidad total incluyendo la merma calculada"
    )
    
    @api.depends('product_qty', 'bom_id.waste_percentage')
    def _compute_waste_qty(self):
        """Calcula la cantidad de merma basada en el porcentaje del BOM"""
        for line in self:
            if line.bom_id.waste_percentage and line.product_qty:
                line.waste_qty = line.product_qty * (line.bom_id.waste_percentage / 100.0)
            else:
                line.waste_qty = 0.0
    
    @api.depends('product_qty', 'waste_qty')
    def _compute_total_qty_with_waste(self):
        """Calcula la cantidad total incluyendo la merma"""
        for line in self:
            line.total_qty_with_waste = line.product_qty + line.waste_qty


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        """
        Sobrescribe el método para incluir la merma en las cantidades de materias primas
        """
        values = super()._get_move_raw_values(
            product_id, product_uom_qty, product_uom, operation_id, bom_line
        )
        
        # Si hay una línea BOM con merma, ajustar la cantidad
        if bom_line and hasattr(bom_line, 'total_qty_with_waste') and bom_line.total_qty_with_waste:
            # Calcular el factor de escala basado en la cantidad de producción
            if bom_line.product_qty > 0:
                scale_factor = values.get('product_uom_qty', product_uom_qty) / bom_line.product_qty
                # Aplicar la cantidad total con merma escalada
                values['product_uom_qty'] = bom_line.total_qty_with_waste * scale_factor
        
        return values
    
    @api.model
    def _get_bom_data(self, bom, warehouse, product=False, product_qty=1, child_bom_ids=[], level=0, parent_bom=False):
        """
        Sobrescribe para incluir información de merma en los datos del BOM
        """
        data = super()._get_bom_data(bom, warehouse, product, product_qty, child_bom_ids, level, parent_bom)
        
        # Agregar información de merma
        if hasattr(bom, 'waste_percentage'):
            data['waste_percentage'] = bom.waste_percentage
            
        # Actualizar las líneas con información de merma
        for line_data in data.get('lines', []):
            bom_line = self.env['mrp.bom.line'].browse(line_data.get('line_id'))
            if bom_line and hasattr(bom_line, 'waste_qty'):
                line_data['waste_qty'] = bom_line.waste_qty
                line_data['total_qty_with_waste'] = bom_line.total_qty_with_waste
                
        return data