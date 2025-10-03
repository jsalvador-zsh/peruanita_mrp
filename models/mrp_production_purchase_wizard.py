# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from collections import defaultdict


class MrpProductionPurchaseWizard(models.TransientModel):
    _name = 'mrp.production.purchase.wizard'
    _description = 'Asistente para Consolidar Componentes y Crear Solicitud de Compra'

    production_ids = fields.Many2many(
        'mrp.production',
        string='Órdenes de Fabricación',
        required=True,
        help="Órdenes de fabricación seleccionadas para consolidar componentes"
    )
    
    line_ids = fields.One2many(
        'mrp.production.purchase.wizard.line',
        'wizard_id',
        string='Componentes Consolidados',
        help="Componentes consolidados de todas las órdenes seleccionadas"
    )
    
    margin_percentage = fields.Float(
        string='% Margen de Stock',
        default=0.0,
        help="Porcentaje adicional que se agregará a las cantidades solicitadas como colchón de stock"
    )
    
    total_products = fields.Integer(
        string='Total de Productos',
        compute='_compute_totals',
        store=True
    )
    
    total_quantity = fields.Float(
        string='Cantidad Total',
        compute='_compute_totals',
        store=True,
        digits='Product Unit of Measure'
    )
    
    notes = fields.Text(
        string='Notas',
        help="Notas adicionales para la solicitud de compra"
    )
    
    @api.depends('line_ids', 'line_ids.quantity_required', 'line_ids.quantity_with_margin')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_products = len(wizard.line_ids)
            wizard.total_quantity = sum(wizard.line_ids.mapped('quantity_with_margin'))
    
    @api.model
    def default_get(self, fields_list):
        """Cargar las órdenes de producción y consolidar sus componentes"""
        res = super().default_get(fields_list)

        # Obtener las órdenes seleccionadas desde el contexto
        production_ids = self.env.context.get('active_ids', [])

        if not production_ids:
            raise UserError('Debe seleccionar al menos una orden de fabricación.')

        productions = self.env['mrp.production'].browse(production_ids)

        # Validar que las órdenes tengan componentes
        has_components = False
        for production in productions:
            if production.move_raw_ids:
                has_components = True
                break

        if not has_components:
            raise UserError('Las órdenes seleccionadas no tienen componentes definidos.')

        res['production_ids'] = [(6, 0, production_ids)]

        # Consolidar componentes de todas las órdenes
        components = self._consolidate_components(productions)

        # Crear líneas del wizard
        line_vals = []
        margin_percentage = res.get('margin_percentage', 0.0)
        for product_id, data in components.items():
            quantity_required = data['quantity']
            quantity_with_margin = quantity_required * (1 + margin_percentage / 100.0)
            line_vals.append((0, 0, {
                'product_id': product_id,
                'quantity_required': quantity_required,
                'quantity_with_margin': quantity_with_margin,
                'product_uom_id': data['uom_id'],
                'production_ids': [(6, 0, data['production_ids'])],
            }))

        res['line_ids'] = line_vals

        return res
    
    def _consolidate_components(self, productions):
        """Consolida los componentes de múltiples órdenes de producción"""
        components = defaultdict(lambda: {
            'quantity': 0.0,
            'uom_id': False,
            'production_ids': []
        })
        
        for production in productions:
            for move in production.move_raw_ids:
                # Solo considerar movimientos que no estén cancelados
                if move.state == 'cancel':
                    continue
                
                product = move.product_id
                
                # Consolidar cantidades (convertir todo a la UdM del producto)
                quantity = move.product_uom_qty
                
                components[product.id]['quantity'] += quantity
                components[product.id]['uom_id'] = move.product_uom.id
                if production.id not in components[product.id]['production_ids']:
                    components[product.id]['production_ids'].append(production.id)
        
        return components
    
    @api.onchange('margin_percentage')
    def _onchange_margin_percentage(self):
        """Recalcular las cantidades con margen cuando cambia el porcentaje"""
        if self.line_ids:
            for line in self.line_ids:
                line.quantity_with_margin = line.quantity_required * (1 + self.margin_percentage / 100.0)
    
    def action_create_purchase_request(self):
        """Crear solicitud de compra con los componentes consolidados"""
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError('No hay componentes para crear la solicitud de compra.')
        
        # Verificar si existe el módulo purchase_request, sino usar purchase.order
        if 'purchase.request' in self.env:
            return self._create_purchase_request()
        else:
            return self._create_purchase_order()
    
    def _create_purchase_request(self):
        """Crear una solicitud de compra (purchase.request)"""
        # Preparar valores para la solicitud de compra
        request_vals = {
            'origin': ', '.join(self.production_ids.mapped('name')),
            'description': self.notes or 'Solicitud consolidada de componentes para producción',
        }
        
        request = self.env['purchase.request'].create(request_vals)
        
        # Crear líneas de la solicitud
        for line in self.line_ids:
            if line.quantity_with_margin > 0:
                self.env['purchase.request.line'].create({
                    'request_id': request.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity_with_margin,
                    'product_uom_id': line.product_uom_id.id,
                    'description': line.notes or line.product_id.display_name,
                })
        
        # Retornar acción para abrir la solicitud creada
        return {
            'type': 'ir.actions.act_window',
            'name': 'Solicitud de Compra',
            'res_model': 'purchase.request',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _prepare_purchase_order_vals(self, supplier_id, origin):
        """
        Preparar valores para crear una orden de compra.
        Este método puede ser extendido en otros módulos para agregar campos personalizados.
        """
        # Crear registro temporal para ejecutar onchanges
        order_temp = self.env['purchase.order'].new({
            'partner_id': supplier_id,
            'origin': origin,
            'notes': self.notes or 'Solicitud consolidada de componentes para producción',
        })
        
        # Ejecutar onchange de partner_id
        order_temp._onchange_partner_id()
        
        # Convertir a diccionario con los valores actualizados
        order_vals = order_temp._convert_to_write(order_temp._cache)
        
        # Asegurar que los valores clave estén presentes
        order_vals.update({
            'partner_id': supplier_id,
            'origin': origin,
            'notes': self.notes or 'Solicitud consolidada de componentes para producción',
        })
        
        return order_vals
    
    def _prepare_purchase_order_line_vals(self, order, line, seller):
        """
        Preparar valores para crear una línea de orden de compra.
        Este método puede ser extendido en otros módulos para agregar campos personalizados.
        """
        # Obtener el nombre del producto
        product_name = line.product_id.display_name
        if line.product_id.description_purchase:
            product_name = line.product_id.description_purchase
        
        # Preparar valores básicos
        po_line_vals = {
            'order_id': order.id,
            'product_id': line.product_id.id,
            'product_qty': line.quantity_with_margin,
            'product_uom': line.product_uom_id.id,
            'date_planned': fields.Datetime.now(),
            'name': line.notes or product_name,
        }
        
        # Establecer precio del seller si existe, sino usar el precio del producto
        if seller and seller.price:
            po_line_vals['price_unit'] = seller.price
        else:
            # Intentar obtener el precio estándar del producto
            po_line_vals['price_unit'] = line.product_id.standard_price or 0.0
        
        # Obtener impuestos del producto
        fpos = order.fiscal_position_id
        taxes = line.product_id.supplier_taxes_id
        if fpos:
            taxes = fpos.map_tax(taxes)
        po_line_vals['taxes_id'] = [(6, 0, taxes.ids)]
        
        return po_line_vals
    
    def _create_purchase_order(self):
        """Crear una orden de compra borrador (purchase.order)"""
        # Agrupar líneas por proveedor
        lines_by_supplier = {}
        lines_without_supplier = []

        for line in self.line_ids:
            if line.quantity_with_margin <= 0:
                continue

            # Buscar el proveedor preferido del producto
            seller = line.product_id._select_seller(
                quantity=line.quantity_with_margin,
                uom_id=line.product_uom_id
            )

            if seller and seller.partner_id:
                supplier_id = seller.partner_id.id
                if supplier_id not in lines_by_supplier:
                    lines_by_supplier[supplier_id] = []
                lines_by_supplier[supplier_id].append((line, seller))
            else:
                lines_without_supplier.append((line, None))

        # Si no hay proveedores definidos, usar proveedor por defecto (ID 1)
        if not lines_by_supplier and lines_without_supplier:
            default_supplier_id = 1
            lines_by_supplier[default_supplier_id] = lines_without_supplier
        elif lines_without_supplier:
            # Si hay líneas sin proveedor pero ya existen otras con proveedor,
            # agregar las sin proveedor al proveedor por defecto (ID 1)
            default_supplier_id = 1
            if default_supplier_id not in lines_by_supplier:
                lines_by_supplier[default_supplier_id] = []
            lines_by_supplier[default_supplier_id].extend(lines_without_supplier)

        # Crear órdenes de compra agrupadas por proveedor
        created_orders = []
        origin = ', '.join(self.production_ids.mapped('name'))

        for supplier_id, lines_data in lines_by_supplier.items():
            try:
                # Preparar valores de la orden usando el método extensible
                order_vals = self._prepare_purchase_order_vals(supplier_id, origin)

                # Crear la orden de compra
                order = self.env['purchase.order'].create(order_vals)

                # Crear líneas de la orden
                for line, seller in lines_data:
                    # Preparar valores de la línea usando el método extensible
                    po_line_vals = self._prepare_purchase_order_line_vals(order, line, seller)

                    # Crear la línea
                    self.env['purchase.order.line'].create(po_line_vals)

                created_orders.append(order)

            except Exception as e:
                # Si hay un error, proporcionar información útil
                error_msg = str(e)
                if 'required' in error_msg.lower() or 'obligatorio' in error_msg.lower():
                    raise UserError(
                        f'Error al crear la orden de compra para el proveedor {self.env["res.partner"].browse(supplier_id).name}:\n\n'
                        f'{error_msg}\n\n'
                        f'Su sistema tiene campos personalizados obligatorios en las órdenes de compra. '
                        f'Por favor, contacte a su administrador de sistema para configurar valores por defecto '
                        f'o extender este wizard para incluir estos campos.'
                    )
                else:
                    raise
        
        # Retornar acción para abrir la(s) orden(es) creada(s)
        if len(created_orders) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Orden de Compra',
                'res_model': 'purchase.order',
                'res_id': created_orders[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Órdenes de Compra Creadas',
                'res_model': 'purchase.order',
                'view_mode': 'list,form',
                'domain': [('id', 'in', [o.id for o in created_orders])],
                'target': 'current',
            }
    
    def action_cancel(self):
        """Cerrar el asistente sin hacer nada"""
        return {'type': 'ir.actions.act_window_close'}


class MrpProductionPurchaseWizardLine(models.TransientModel):
    _name = 'mrp.production.purchase.wizard.line'
    _description = 'Línea del Asistente de Consolidación para Compras'
    _order = 'product_id'

    wizard_id = fields.Many2one(
        'mrp.production.purchase.wizard',
        string='Asistente',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        readonly=True
    )
    
    quantity_required = fields.Float(
        string='Cantidad Requerida',
        required=True,
        digits='Product Unit of Measure',
        help="Cantidad total requerida de todas las órdenes de producción"
    )
    
    quantity_with_margin = fields.Float(
        string='Cantidad con Margen',
        required=True,
        digits='Product Unit of Measure',
        help="Cantidad requerida más el porcentaje de margen"
    )
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de Medida',
        required=True
    )
    
    production_ids = fields.Many2many(
        'mrp.production',
        string='Órdenes de Producción',
        help="Órdenes de producción que requieren este componente"
    )
    
    production_count = fields.Integer(
        string='# Órdenes',
        compute='_compute_production_count'
    )
    
    notes = fields.Char(
        string='Notas',
        help="Notas adicionales para este componente"
    )
    
    # Campos relacionados del producto
    default_code = fields.Char(
        related='product_id.default_code',
        string='Referencia Interna',
        readonly=True
    )
    
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id',
        string='Plantilla de Producto',
        readonly=True
    )
    
    @api.depends('production_ids')
    def _compute_production_count(self):
        for line in self:
            line.production_count = len(line.production_ids)
    
    def action_view_productions(self):
        """Acción para ver las órdenes de producción relacionadas"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes de Producción',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.production_ids.ids)],
            'target': 'current',
        }
