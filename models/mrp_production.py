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
    
    sale_distributor_id = fields.Many2one(
        'res.partner',
        string='Distribuidor',
        compute='_compute_sale_distributor_id',
        store=True,
        readonly=True,
        help="Distribuidor de la orden de venta relacionada con esta orden de fabricación"
    )
    
    has_sale_order = fields.Boolean(
        string='Tiene Orden de Venta',
        compute='_compute_has_sale_order',
        store=True,
        help="Indica si esta orden de fabricación tiene una orden de venta relacionada"
    )
    
    batch_id = fields.Many2one(
        'stock.picking.batch',
        string='Batch de Traslados',
        readonly=True,
        help="Batch que agrupa los traslados de materia prima de esta orden",
        copy=False
    )
    
    raw_material_picking_ids = fields.Many2many(
        'stock.picking',
        compute='_compute_raw_material_picking_ids',
        string='Traslados de MP',
        help="Traslados de materia prima relacionados a esta orden"
    )
    
    raw_material_picking_count = fields.Integer(
        string='# Traslados MP',
        compute='_compute_raw_material_picking_ids',
    )
    
    @api.depends('picking_ids')
    def _compute_raw_material_picking_ids(self):
        """Calcula los traslados de materia prima relacionados"""
        for production in self:
            # Usar el campo picking_ids que ya existe en Odoo
            # Primero intentar con pickings internos
            pickings = production.picking_ids.filtered(
                lambda p: p.picking_type_id.code == 'internal'
            )
            
            # Si no hay pickings internos, tomar todos excepto outgoing (entregas)
            if not pickings:
                pickings = production.picking_ids.filtered(
                    lambda p: p.picking_type_id.code != 'outgoing'
                )
            
            production.raw_material_picking_ids = pickings
            production.raw_material_picking_count = len(pickings)
    
    @api.depends('move_dest_ids', 'move_dest_ids.group_id', 'move_dest_ids.group_id.sale_id')
    def _compute_sale_partner_id(self):
        """Calcula el cliente basado en la orden de venta relacionada"""
        for production in self:
            sale_order = self._get_related_sale_order(production)
            production.sale_partner_id = sale_order.partner_id if sale_order else False
    
    @api.depends('move_dest_ids', 'move_dest_ids.group_id', 'move_dest_ids.group_id.sale_id')
    def _compute_sale_distributor_id(self):
        """Calcula el distribuidor basado en la orden de venta relacionada"""
        for production in self:
            sale_order = self._get_related_sale_order(production)
            production.sale_distributor_id = sale_order.distributor_id if sale_order and hasattr(sale_order, 'distributor_id') else False
    
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
    
    def action_view_raw_material_pickings(self):
        """Acción para ver los traslados de materia prima"""
        self.ensure_one()
        pickings = self.raw_material_picking_ids
        
        if not pickings:
            return
        
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif len(pickings) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        
        return action
    
    def action_view_batch(self):
        """Acción para ver el batch relacionado"""
        self.ensure_one()
        if not self.batch_id:
            return
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Batch de Traslados',
            'res_model': 'stock.picking.batch',
            'res_id': self.batch_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_consolidate_productions(self):
        """Abre el asistente para consolidar órdenes de fabricación"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consolidar Órdenes de Fabricación',
            'res_model': 'mrp.production.batch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }