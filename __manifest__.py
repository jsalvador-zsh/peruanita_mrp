{
    'name': 'Peruanita MRP - Planificación y Consolidación de Producción',
    'version': '18.0.2.0.0',
    'category': 'Manufacturing',
    'summary': 'Planificación mensual, consolidación de componentes, solicitudes de compra y control de calidad',
    'description': """
        Este módulo extiende las órdenes de fabricación con funcionalidades avanzadas
        de planificación, consolidación y control de calidad.

        Características:
        * Campo cliente y distribuidor calculado automáticamente
        * Consolidación de órdenes de fabricación para crear batches de traslados
        * Consolidación de componentes con margen de stock configurable
        * Generación automática de solicitudes de compra agrupadas por proveedor
        * Edición manual de cantidades consolidadas
        * Control de calidad para recepciones con validación obligatoria
        * Gestión de certificados de calidad de lotes
        * Compatible con Odoo 18
    """,
    'author': 'Juan Salvador',
    'website': 'https://jsalvador.dev',
    'depends': [
        'mrp',
        'sale_mrp',
        'purchase',
        'stock'
    ],
    'data': [
        'security/product_lot_quality_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/cron_data.xml',
        'views/mrp_production_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_batch_wizard_views.xml',
        'views/mrp_production_purchase_wizard_views.xml',
        'views/product_lot_quality_views.xml',
        'views/stock_picking_quality_views.xml',
        'wizard/stock_picking_quality_wizard_views.xml',
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