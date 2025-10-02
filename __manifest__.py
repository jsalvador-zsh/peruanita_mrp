{
    'name': 'Peruanita MRP - Cliente en Orden de Fabricación',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Muestra el cliente relacionado en órdenes de fabricación cuando provienen de una venta',
    'description': """
        Este módulo extiende las órdenes de fabricación para mostrar automáticamente
        el cliente cuando la orden proviene de una venta relacionada.
        
        Características:
        * Campo cliente calculado automáticamente
        * Solo visible cuando hay una venta relacionada
        * Compatible con Odoo 18
    """,
    'author': 'Juan Salvador',
    'website': 'https://jsalvador.dev',
    'depends': [
        'mrp',
        'sale_mrp'
    ],
    'data': [
        'views/mrp_production_views.xml',
        'views/mrp_bom_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}