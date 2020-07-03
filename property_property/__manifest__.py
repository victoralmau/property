# -*- coding: utf-8 -*-
{
    'name': 'Ont Property Property',
    'version': '10.0.1.0.0',    
    'author': 'Odoo Nodriza Tech (ONT)',
    'website': 'https://nodrizatech.com/',
    'category': 'Tools',
    'license': 'AGPL-3',
    'depends': ['base', 'property_distritopostal'],
    'external_dependencies': {
        'python' : ['xmltodict'],
    },
    'data': [
        'data/ir_configparameter_data.xml',
        'data/ir_cron.xml',
        'security/ir.model.access.csv',                         
    ],
    'installable': True,
    'auto_install': False,    
}