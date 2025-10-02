from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        compute='_compute_sale_partner_id',
        store=True,
        readonly=True,
        help="Cliente de la orden de venta relacionada con esta orden de fabricación"
    )
    
    has_sale_order = fields.Boolean(
        string='Tiene Orden de Venta',
        compute='_compute_has_sale_order',
        store=True,
        help="Indica si esta orden de fabricación tiene una orden de venta relacionada"
    )
    
    @api.depends('move_dest_ids', 'move_dest_ids.group_id', 'move_dest_ids.group_id.sale_id')
    def _compute_sale_partner_id(self):
        """Calcula el cliente basado en la orden de venta relacionada"""
        for production in self:
            sale_order = self._get_related_sale_order(production)
            production.sale_partner_id = sale_order.partner_id if sale_order else False
    
    @api.depends('sale_partner_id')
    def _compute_has_sale_order(self):
        """Determina si hay una orden de venta relacionada"""
        for production in self:
            production.has_sale_order = bool(production.sale_partner_id)
    
    def _get_related_sale_order(self, production):
        """
        Obtiene la orden de venta relacionada con la orden de fabricación
        Busca a través de los movimientos de destino y sus grupos de aprovisionamiento
        """
        sale_order = False
        
        # Método 1: A través de move_dest_ids y procurement group
        for move in production.move_dest_ids:
            if move.group_id and move.group_id.sale_id:
                sale_order = move.group_id.sale_id
                break
        
        # Método 2: A través de las líneas de la orden de venta directamente
        if not sale_order:
            sale_line_obj = self.env['sale.order.line']
            sale_lines = sale_line_obj.search([
                ('product_id', '=', production.product_id.id),
                ('qty_to_deliver', '>', 0)
            ])
            for line in sale_lines:
                # Verificar si esta línea podría estar relacionada con nuestra producción
                if line.product_id == production.product_id:
                    sale_order = line.order_id
                    break
        
        return sale_order
    
    def action_view_sale_order(self):
        """Acción para ver la orden de venta relacionada"""
        self.ensure_one()
        sale_order = self._get_related_sale_order(self)
        if not sale_order:
            return
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Orden de Venta',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }