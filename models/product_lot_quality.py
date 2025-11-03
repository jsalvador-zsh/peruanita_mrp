# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


class ProductLotQuality(models.Model):
    _name = 'product.lot.quality'
    _description = 'Certificado de Calidad de Lote'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'certificate_expiry_date desc, name'

    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        tracking=True,
        domain="[('type', '=', 'consu'), ('tracking', '=', 'lot')]",
        help='Producto almacenable con rastreabilidad por lote'
    )

    lot_id = fields.Many2one(
        'stock.lot',
        string='Lote',
        required=True,
        tracking=True,
        ondelete='restrict',
        help='Lote del producto al que se asocia este certificado',
        domain="[('product_id', '=', product_id)]"
    )

    name = fields.Char(
        string='Número de Lote',
        related='lot_id.name',
        store=True,
        readonly=True,
        help='Número identificador del lote'
    )

    certificate_issue_date = fields.Date(
        string='Fecha de Emisión del Certificado',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help='Fecha en que se emitió el certificado de calidad'
    )

    certificate_expiry_date = fields.Date(
        string='Fecha de Vencimiento del Certificado',
        required=True,
        tracking=True,
        help='Fecha de vencimiento del certificado de calidad (4 meses desde emisión)',
        compute='_compute_expiry_date',
        store=True,
        readonly=False
    )

    days_to_expire = fields.Integer(
        string='Días para Vencer',
        compute='_compute_days_to_expire',
        store=True,
        help='Días restantes hasta el vencimiento del certificado'
    )

    state = fields.Selection([
        ('valid', 'Vigente'),
        ('warning', 'Por Vencer'),
        ('expired', 'Vencido')
    ], string='Estado', compute='_compute_state', store=True, tracking=True)

    certificate_number = fields.Char(
        string='Número de Certificado',
        tracking=True,
        help='Número del certificado de calidad'
    )

    notes = fields.Text(
        string='Observaciones',
        help='Notas adicionales sobre el certificado'
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está inactivo, el lote no aparecerá en las búsquedas estándar'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )

    # Campo calculado para mostrar el producto con variantes
    product_display_name = fields.Char(
        string='Producto',
        related='product_id.display_name',
        readonly=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Limpiar el lote cuando se cambia el producto"""
        if self.product_id and self.lot_id and self.lot_id.product_id != self.product_id:
            self.lot_id = False

    @api.depends('certificate_issue_date')
    def _compute_expiry_date(self):
        """Calcula automáticamente la fecha de vencimiento (4 meses desde emisión)"""
        for record in self:
            if record.certificate_issue_date:
                # Sumar 4 meses a la fecha de emisión
                record.certificate_expiry_date = record.certificate_issue_date + relativedelta(months=4)
            else:
                record.certificate_expiry_date = False

    @api.depends('certificate_expiry_date')
    def _compute_days_to_expire(self):
        """Calcula los días restantes hasta el vencimiento"""
        today = fields.Date.context_today(self)
        for record in self:
            if record.certificate_expiry_date:
                delta = record.certificate_expiry_date - today
                record.days_to_expire = delta.days
            else:
                record.days_to_expire = 0

    @api.depends('days_to_expire', 'certificate_expiry_date')
    def _compute_state(self):
        """Calcula el estado del certificado basado en días para vencer"""
        for record in self:
            if not record.certificate_expiry_date:
                record.state = 'valid'
            elif record.days_to_expire < 0:
                record.state = 'expired'
            elif record.days_to_expire <= 15:  # Alerta 15 días antes
                record.state = 'warning'
            else:
                record.state = 'valid'

    @api.model
    def _cron_check_expiring_certificates(self):
        """
        Cron job que verifica certificados por vencer y crea actividades
        para administradores del módulo de manufactura
        """
        # Buscar certificados que vencen en los próximos 15 días y aún no tienen actividad
        warning_date = fields.Date.context_today(self) + timedelta(days=15)
        expiring_certificates = self.search([
            ('certificate_expiry_date', '<=', warning_date),
            ('certificate_expiry_date', '>=', fields.Date.context_today(self)),
            ('state', '=', 'warning'),
            ('active', '=', True)
        ])

        # Buscar certificados vencidos
        expired_certificates = self.search([
            ('certificate_expiry_date', '<', fields.Date.context_today(self)),
            ('state', '=', 'expired'),
            ('active', '=', True)
        ])

        # Obtener usuarios con permiso de notificaciones de certificados
        notification_group = self.env.ref('peruanita_mrp.group_quality_certificate_notifications', raise_if_not_found=False)
        if not notification_group:
            return

        notifiable_users = notification_group.users

        for certificate in expiring_certificates:
            # Verificar si ya existe una actividad pendiente para este certificado
            existing_activity = self.env['mail.activity'].search([
                ('res_id', '=', certificate.id),
                ('res_model_id', '=', self.env['ir.model']._get('product.lot.quality').id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_warning').id),
                ('state', '!=', 'done')
            ], limit=1)

            if not existing_activity:
                # Crear actividad para cada usuario con permisos de notificación
                for user in notifiable_users:
                    self.env['mail.activity'].create({
                        'res_id': certificate.id,
                        'res_model_id': self.env['ir.model']._get('product.lot.quality').id,
                        'activity_type_id': self.env.ref('mail.mail_activity_data_warning').id,
                        'summary': f'Certificado de calidad por vencer - Lote {certificate.name}',
                        'note': f'El certificado de calidad del lote {certificate.name} vencerá en {certificate.days_to_expire} días (Fecha de vencimiento: {certificate.certificate_expiry_date}).',
                        'date_deadline': certificate.certificate_expiry_date,
                        'user_id': user.id,
                    })

        for certificate in expired_certificates:
            # Verificar si ya existe una actividad pendiente para este certificado vencido
            existing_activity = self.env['mail.activity'].search([
                ('res_id', '=', certificate.id),
                ('res_model_id', '=', self.env['ir.model']._get('product.lot.quality').id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ('state', '!=', 'done')
            ], limit=1)

            if not existing_activity:
                # Crear actividad urgente para cada usuario con permisos de notificación
                for user in notifiable_users:
                    self.env['mail.activity'].create({
                        'res_id': certificate.id,
                        'res_model_id': self.env['ir.model']._get('product.lot.quality').id,
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'summary': f'URGENTE: Certificado de calidad vencido - Lote {certificate.name}',
                        'note': f'El certificado de calidad del lote {certificate.name} para el producto {certificate.product_id.display_name} está VENCIDO desde {abs(certificate.days_to_expire)} días (Fecha de vencimiento: {certificate.certificate_expiry_date}). Se requiere acción inmediata.',
                        'date_deadline': fields.Date.context_today(self),
                        'user_id': user.id,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        """Override create para crear actividad inicial si el certificado está por vencer"""
        records = super(ProductLotQuality, self).create(vals_list)
        records._check_and_create_activities()
        return records

    def write(self, vals):
        """Override write para actualizar actividades si cambia la fecha de vencimiento"""
        result = super(ProductLotQuality, self).write(vals)
        if 'certificate_expiry_date' in vals or 'certificate_issue_date' in vals:
            self._check_and_create_activities()
        return result

    def _check_and_create_activities(self):
        """Método auxiliar para verificar y crear actividades si es necesario"""
        # Obtener usuarios con permiso de notificaciones de certificados
        notification_group = self.env.ref('peruanita_mrp.group_quality_certificate_notifications', raise_if_not_found=False)
        if not notification_group:
            return

        notifiable_users = notification_group.users
        if not notifiable_users:
            return

        for record in self:
            if record.state in ['warning', 'expired']:
                # Verificar si ya existe una actividad pendiente
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', record.id),
                    ('res_model_id', '=', self.env['ir.model']._get('product.lot.quality').id),
                    ('state', '!=', 'done')
                ], limit=1)

                if not existing_activity:
                    activity_type = self.env.ref('mail.mail_activity_data_todo') if record.state == 'expired' else self.env.ref('mail.mail_activity_data_warning')

                    for user in notifiable_users:
                        summary = f'{"URGENTE: Certificado vencido" if record.state == "expired" else "Certificado por vencer"} - Lote {record.name}'
                        note = f'El certificado de calidad del lote {record.name} para el producto {record.product_id.display_name} {"está VENCIDO" if record.state == "expired" else "está por vencer"} (Vencimiento: {record.certificate_expiry_date}).'

                        self.env['mail.activity'].create({
                            'res_id': record.id,
                            'res_model_id': self.env['ir.model']._get('product.lot.quality').id,
                            'activity_type_id': activity_type.id,
                            'summary': summary,
                            'note': note,
                            'date_deadline': record.certificate_expiry_date if record.state == 'warning' else fields.Date.context_today(self),
                            'user_id': user.id,
                        })

    def action_renew_certificate(self):
        """Acción para renovar el certificado (crear uno nuevo)"""
        self.ensure_one()
        return {
            'name': 'Renovar Certificado',
            'type': 'ir.actions.act_window',
            'res_model': 'product.lot.quality',
            'view_mode': 'form',
            'context': {
                'default_lot_id': self.lot_id.id,
                'default_certificate_issue_date': fields.Date.context_today(self),
            },
            'target': 'new',
        }

    _sql_constraints = [
        ('lot_unique', 'unique(lot_id, company_id)',
         'Ya existe un certificado de calidad para este lote en esta compañía!'),
    ]
