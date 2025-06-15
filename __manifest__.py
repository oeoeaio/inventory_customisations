{
    'name': 'Inventory Customisations',
    'version': '1.0',
    'depends': ['stock'],
    'author': 'Rob Harrington',
    'category': 'Inventory',
    'description': 'Customisations to inventory functionality',
    'data': [
        'security/ir.model.access.csv',
        'wizard/bulk_replenishment_wizard.xml',
        'wizard/inventory_by_route_wizard.xml',
    ],
    'installable': True,
    'application': False,
}
