from odoo import models, fields, api
from odoo.exceptions import UserError


class MrpProductionBatchWizard(models.TransientModel):
    _name = 'mrp.production.batch.wizard'
    _description = 'Asistente para Consolidar Órdenes de Fabricación'

    production_ids = fields.Many2many(
        'mrp.production',
        string='Órdenes de Fabricación',
        required=True,
        help="Órdenes de fabricación seleccionadas para consolidar"
    )
    
    picking_ids = fields.Many2many(
        'stock.picking',
        'mrp_batch_wizard_picking_rel',
        'wizard_id',
        'picking_id',
        string='Traslados Disponibles',
        help="Traslados internos relacionados a las órdenes seleccionadas"
    )
    
    selected_picking_ids = fields.Many2many(
        'stock.picking',
        'mrp_batch_wizard_picking_selected_rel',
        'wizard_id',
        'picking_id',
        string='Traslados Seleccionados',
        help="Traslados que se incluirán en el batch"
    )
    
    batch_name = fields.Char(
        string='Nombre del Batch',
        help="Nombre para el batch de traslados"
    )
    
    batch_description = fields.Text(
        string='Descripción',
        help="Descripción del batch de traslados"
    )
    
    total_pickings = fields.Integer(
        string='Total de Traslados',
        compute='_compute_totals',
        store=True
    )
    
    total_productions = fields.Integer(
        string='Total de Órdenes',
        compute='_compute_totals',
        store=True
    )
    
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Tipo de Operación',
        compute='_compute_picking_type',
        store=True
    )
    
    @api.depends('picking_ids')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_pickings = len(wizard.picking_ids)
            wizard.total_productions = len(wizard.production_ids)
    
    @api.depends('picking_ids')
    def _compute_picking_type(self):
        for wizard in self:
            if wizard.picking_ids:
                wizard.picking_type_id = wizard.picking_ids[0].picking_type_id
            else:
                wizard.picking_type_id = False
    
    @api.model
    def default_get(self, fields_list):
        """Cargar las órdenes de producción seleccionadas desde el contexto"""
        res = super().default_get(fields_list)
        
        # Obtener las órdenes seleccionadas desde el contexto
        production_ids = self.env.context.get('active_ids', [])
        
        if not production_ids:
            raise UserError('Debe seleccionar al menos una orden de fabricación.')
        
        productions = self.env['mrp.production'].browse(production_ids)
        
        # Validar que las órdenes no estén ya en un batch
        for production in productions:
            if production.batch_id:
                raise UserError(
                    f'La orden {production.name} ya está asignada al batch {production.batch_id.name}'
                )
        
        res['production_ids'] = [(6, 0, production_ids)]
        
        # Buscar los pickings relacionados (traslados de materia prima)
        all_pickings = self.env['stock.picking']
        for production in productions:
            # Usar el campo picking_ids que ya existe en mrp.production
            # Primero intentar con pickings internos
            pickings = production.picking_ids.filtered(
                lambda p: p.picking_type_id.code == 'internal'
            )
            
            # Si no hay pickings internos, tomar todos los pickings
            # que no sean de tipo 'outgoing' (entregas a clientes)
            if not pickings:
                pickings = production.picking_ids.filtered(
                    lambda p: p.picking_type_id.code != 'outgoing'
                )
            
            all_pickings |= pickings
        
        if not all_pickings:
            raise UserError(
                'No se encontraron traslados de materia prima relacionados a las órdenes seleccionadas.'
            )
        
        res['picking_ids'] = [(6, 0, all_pickings.ids)]
        res['selected_picking_ids'] = [(6, 0, all_pickings.ids)]
        
        return res
    
    def action_create_batch(self):
        """Crear el batch de traslados con los pickings seleccionados"""
        self.ensure_one()
        
        # Validar que haya al menos un picking seleccionado
        if not self.selected_picking_ids:
            raise UserError('Debe seleccionar al menos un traslado para crear el batch.')
        
        # Validar que todos los pickings sean del mismo tipo
        picking_types = self.selected_picking_ids.mapped('picking_type_id')
        if len(picking_types) > 1:
            raise UserError('Todos los traslados deben ser del mismo tipo de operación.')
        
        # Crear el batch de traslados
        batch_vals = {
            'name': self.batch_name or False,
            'picking_type_id': picking_types[0].id,
            'picking_ids': [(6, 0, self.selected_picking_ids.ids)],
        }
        
        if self.batch_description:
            batch_vals['description'] = self.batch_description
        
        batch = self.env['stock.picking.batch'].create(batch_vals)
        
        # Actualizar las órdenes de producción con el batch_id
        # Solo actualizar las que tienen pickings seleccionados
        productions_to_update = self.env['mrp.production']
        for production in self.production_ids:
            production_pickings = production.picking_ids & self.selected_picking_ids
            if production_pickings:
                productions_to_update |= production
        
        if productions_to_update:
            productions_to_update.write({'batch_id': batch.id})
        
        # Retornar la acción para abrir el batch creado
        return {
            'type': 'ir.actions.act_window',
            'name': 'Batch de Traslados',
            'res_model': 'stock.picking.batch',
            'res_id': batch.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_cancel(self):
        """Cerrar el asistente sin hacer nada"""
        return {'type': 'ir.actions.act_window_close'}