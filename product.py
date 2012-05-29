#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval


class Product(ModelSQL, ModelView):
    _name = 'product.product'

    locations = fields.One2Many('stock.product.location', 'product',
        'Default Locations', states={
            'invisible': ~Eval('type').in_(['goods', 'assets']),
            })

Product()
