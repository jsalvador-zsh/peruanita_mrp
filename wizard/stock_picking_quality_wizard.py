# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPickingQualityWizard(models.TransientModel):
    """Wizard para Control de Calidad de Recepción"""
    _name = 'stock.picking.quality.wizard'
    _description = 'Wizard de Control de Calidad'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Recepción',
        required=True,
        readonly=True
    )

    findings = fields.Text(
        string='Descripción del Control',
        required=True,
        help='Describa lo encontrado durante el control de calidad'
    )

    state = fields.Selection([
        ('approved', 'Aprobado'),
        ('rejected', 'Desaprobado')
    ], string='Resultado', required=True, default='approved')

    def action_confirm(self):
        """Guarda el control de calidad"""
        self.ensure_one()

        # Crear el registro de control de calidad
        inspection = self.env['stock.picking.quality.inspection'].create({
            'picking_id': self.picking_id.id,
            'findings': self.findings,
            'state': self.state,
        })

        # Mostrar mensaje
        if self.state == 'approved':
            message = 'Control de calidad aprobado.'
        else:
            message = 'Control de calidad desaprobado.'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Control de Calidad',
                'message': message,
                'type': 'success' if self.state == 'approved' else 'warning',
                'sticky': False,
            }
        }
