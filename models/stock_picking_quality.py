# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPickingQualityInspection(models.Model):
    """Control de Calidad para Recepciones"""
    _name = 'stock.picking.quality.inspection'
    _description = 'Control de Calidad de Recepción'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inspection_date desc, id desc'

    name = fields.Char(
        string='Número de Control',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: 'Nuevo',
        tracking=True
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Recepción',
        required=True,
        ondelete='cascade',
        tracking=True,
        domain="[('picking_type_code', '=', 'incoming')]",
        help='Recepción de inventario asociada a este control'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        related='picking_id.partner_id',
        store=True,
        readonly=True
    )

    inspection_date = fields.Datetime(
        string='Fecha de Control',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )

    inspector_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        help='Usuario responsable del control de calidad'
    )

    state = fields.Selection([
        ('approved', 'Aprobado'),
        ('rejected', 'Desaprobado')
    ], string='Estado', required=True, tracking=True, copy=False)

    findings = fields.Text(
        string='Hallazgos',
        required=True,
        tracking=True,
        help='Descripción de lo encontrado durante el control de calidad'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Genera secuencia automática para el número de control"""
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.picking.quality.inspection') or 'Nuevo'

            # Actualizar el picking según el estado
            if 'picking_id' in vals and 'state' in vals:
                picking = self.env['stock.picking'].browse(vals['picking_id'])
                picking.quality_inspection_approved = (vals['state'] == 'approved')

        records = super(StockPickingQualityInspection, self).create(vals_list)

        for record in records:
            if record.state == 'approved':
                record.message_post(body=f'Control de calidad aprobado por {record.inspector_id.name}.')
            else:
                record.message_post(body=f'Control de calidad desaprobado por {record.inspector_id.name}.')

        return records

    def write(self, vals):
        """Actualiza el picking cuando cambia el estado"""
        result = super(StockPickingQualityInspection, self).write(vals)

        if 'state' in vals:
            for record in self:
                record.picking_id.quality_inspection_approved = (record.state == 'approved')

                if record.state == 'approved':
                    record.message_post(body=f'Control de calidad aprobado por {self.env.user.name}.')
                else:
                    record.message_post(body=f'Control de calidad desaprobado por {self.env.user.name}.')

        return result


class StockPicking(models.Model):
    """Extensión de Stock Picking para Control de Calidad"""
    _inherit = 'stock.picking'

    quality_inspection_ids = fields.One2many(
        'stock.picking.quality.inspection',
        'picking_id',
        string='Controles de Calidad'
    )

    quality_inspection_count = fields.Integer(
        string='Controles de Calidad',
        compute='_compute_quality_inspection_count'
    )

    quality_inspection_approved = fields.Boolean(
        string='Control de Calidad Aprobado',
        compute='_compute_quality_inspection_approved',
        store=True,
        help='Indica si el control de calidad ha sido aprobado'
    )

    @api.depends('quality_inspection_ids')
    def _compute_quality_inspection_count(self):
        """Cuenta los controles de calidad"""
        for picking in self:
            picking.quality_inspection_count = len(picking.quality_inspection_ids)

    @api.depends('quality_inspection_ids', 'quality_inspection_ids.state')
    def _compute_quality_inspection_approved(self):
        """Determina si hay un control de calidad aprobado"""
        for picking in self:
            approved = picking.quality_inspection_ids.filtered(lambda i: i.state == 'approved')
            picking.quality_inspection_approved = bool(approved)

    def action_quality_control(self):
        """Abre el wizard de control de calidad"""
        self.ensure_one()

        if self.picking_type_code != 'incoming':
            raise UserError('Solo las recepciones requieren control de calidad.')

        return {
            'name': 'Control de Calidad',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.quality.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }

    def action_view_quality_inspections(self):
        """Abre la vista de controles de calidad existentes"""
        self.ensure_one()

        action = {
            'name': 'Controles de Calidad',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.quality.inspection',
            'domain': [('picking_id', '=', self.id)],
            'context': {'default_picking_id': self.id},
        }

        if self.quality_inspection_count == 1:
            action.update({
                'res_id': self.quality_inspection_ids[0].id,
                'view_mode': 'form',
                'views': [(False, 'form')],
            })
        else:
            action['view_mode'] = 'list,form'

        return action

    def button_validate(self):
        """Override para validar control de calidad antes de validar recepción"""
        for picking in self:
            # Solo verificar para recepciones
            if picking.picking_type_code == 'incoming':
                if not picking.quality_inspection_approved:
                    raise UserError(
                        'No se puede validar esta recepción sin un control de calidad aprobado.\n'
                        'Por favor, realice el control de calidad y apruébelo antes de continuar.'
                    )

        return super(StockPicking, self).button_validate()
