{
    'name': 'Peruanita MRP - Planificación y Consolidación de Producción',
    'version': '18.0.2.0.0',
    'category': 'Manufacturing',
    'summary': 'Planificación mensual, consolidación de componentes y solicitudes de compra para manufactura',
    'description': """
        Este módulo extiende las órdenes de fabricación con funcionalidades avanzadas
        de planificación y consolidación.
        
        Características:
        * Campo cliente y distribuidor calculado automáticamente
        * Consolidación de órdenes de fabricación para crear batches de traslados
        * Consolidación de componentes con margen de stock configurable
        * Generación automática de solicitudes de compra agrupadas por proveedor
        * Edición manual de cantidades consolidadas
        * Compatible con Odoo 18
    """,
    'author': 'Juan Salvador',
    'website': 'https://jsalvador.dev',
    'depends': [
        'mrp',
        'sale_mrp',
        'purchase'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_production_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_batch_wizard_views.xml',
        'views/mrp_production_purchase_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'peruanita_mrp/static/src/css/styles.css',
        ]
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}