from odoo import models, fields

class MrpConsolidationWizard(models.TransientModel):
    _name = 'mrp.consolidation.wizard'
    _description = 'Wizard para Consolidación de Órdenes'

    name = fields.Char('Nombre de Consolidación', required=True, default='Consolidación ')
    production_ids = fields.Many2many('mrp.production', string='Órdenes de Producción')
    group_by_category = fields.Boolean('Agrupar por Categoría', default=True)
    include_confirmed = fields.Boolean('Incluir Confirmadas', default=True)
    include_progress = fields.Boolean('Incluir En Progreso', default=True)
    
    def create_consolidation(self):
        """Crea la consolidación con las órdenes seleccionadas"""
        consolidation = self.env['mrp.consolidation'].create({
            'name': self.name,
            'production_ids': [(6, 0, self.production_ids.ids)],
        })
        
        consolidation.calculate_consolidation()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consolidación de Materiales',
            'res_model': 'mrp.consolidation',
            'res_id': consolidation.id,
            'view_mode': 'form',
            'target': 'current',
        }