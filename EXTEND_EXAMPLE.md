# Ejemplo: Cómo Extender el Wizard para Campos Personalizados

Si tu sistema tiene campos personalizados obligatorios en `purchase.order`, puedes crear un pequeño módulo que extienda el wizard para incluir estos campos.

## Crear un Módulo de Extensión

### 1. Estructura del Módulo

```
peruanita_mrp_purchase_extend/
├── __init__.py
├── __manifest__.py
└── models/
    ├── __init__.py
    └── mrp_production_purchase_wizard.py
```

### 2. `__manifest__.py`

```python
{
    'name': 'Peruanita MRP Purchase Wizard - Extensión',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'depends': [
        'peruanita_mrp',
        # Agregar aquí tus módulos personalizados que extienden purchase.order
    ],
    'data': [],
    'installable': True,
    'auto_install': True,  # Se instalará automáticamente si peruanita_mrp está instalado
    'license': 'LGPL-3',
}
```

### 3. `__init__.py` (raíz)

```python
from . import models
```

### 4. `models/__init__.py`

```python
from . import mrp_production_purchase_wizard
```

### 5. `models/mrp_production_purchase_wizard.py`

```python
# -*- coding: utf-8 -*-
from odoo import models

class MrpProductionPurchaseWizard(models.TransientModel):
    _inherit = 'mrp.production.purchase.wizard'

    def _prepare_purchase_order_vals(self, supplier_id, origin):
        """
        Extender el método para agregar campos personalizados
        """
        # Obtener los valores base del método padre
        vals = super()._prepare_purchase_order_vals(supplier_id, origin)
        
        # Agregar tus campos personalizados aquí
        vals.update({
            # Ejemplo: Si tienes un campo is_service_order
            # 'is_service_order': False,
            
            # Ejemplo: Si tienes un campo requester_id
            # 'requester_id': self.env.user.id,
            
            # Ejemplo: Si tienes un campo requesting_department_id
            # 'requesting_department_id': self.env.user.department_id.id,
            
            # Agrega todos los campos obligatorios de tu sistema aquí
        })
        
        return vals
```

## Ejemplo Completo con Campos Comunes

Basándome en tu JSON, aquí está un ejemplo completo:

```python
# -*- coding: utf-8 -*-
from odoo import models

class MrpProductionPurchaseWizard(models.TransientModel):
    _inherit = 'mrp.production.purchase.wizard'

    def _prepare_purchase_order_vals(self, supplier_id, origin):
        """
        Agregar campos personalizados para órdenes de servicio/compra
        """
        vals = super()._prepare_purchase_order_vals(supplier_id, origin)
        
        # Campos personalizados de tu sistema
        vals.update({
            # Tipo de orden
            'is_service_order': False,  # Cambiar a True si es orden de servicio
            'is_distribution_order': False,
            
            # Usuario y departamento
            'requester_id': self.env.user.id,
            'requesting_department_id': self.env.user.employee_id.department_id.id if hasattr(self.env.user, 'employee_id') else False,
            
            # Otros campos que puedan ser obligatorios
            'service_type': 'local',  # o el valor por defecto que uses
            'elaborated_by': self.env.user.name,
            
            # Si tienes un campo product_id en purchase.order (no común)
            # Puedes dejarlo False o poner el primer producto
            # 'product_id': False,
        })
        
        return vals
    
    def _prepare_purchase_order_line_vals(self, order, line, seller):
        """
        Si necesitas agregar campos personalizados a las líneas
        """
        vals = super()._prepare_purchase_order_line_vals(order, line, seller)
        
        # Agregar campos personalizados de la línea aquí si es necesario
        # vals.update({
        #     'campo_personalizado': valor,
        # })
        
        return vals
```

## Instalación

1. Copia el módulo a tu directorio de addons
2. Actualiza la lista de aplicaciones en Odoo
3. Instala el módulo `peruanita_mrp_purchase_extend`
4. El wizard ahora incluirá los campos personalizados automáticamente

## Notas Importantes

- Reemplaza los valores de ejemplo con los campos reales de tu sistema
- Verifica los nombres exactos de los campos en tu modelo `purchase.order`
- Asegúrate de que los valores por defecto sean válidos para tu caso de uso
- Si un campo depende de otro, asegúrate de establecerlos en el orden correcto
