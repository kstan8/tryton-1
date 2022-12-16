#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import Workflow, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.backend import TableHandler

__all__ = ['Invoice', 'InvoiceLine']
__metaclass__ = PoolMeta


class Invoice:
    __name__ = 'account.invoice'
    sales = fields.Many2Many('sale.sale-account.invoice',
            'invoice', 'sale', 'Sales', readonly=True)
    sale_exception_state = fields.Function(fields.Selection([
        ('', ''),
        ('ignored', 'Ignored'),
        ('recreated', 'Recreated'),
        ], 'Exception State'), 'get_sale_exception_state')

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._error_messages.update({
                'delete_sale_invoice': ('You can not delete invoices '
                    'that come from a sale.'),
                'reset_invoice_sale': ('You cannot reset to draft '
                    'an invoice generated by a sale.'),
                })

    @classmethod
    def get_sale_exception_state(cls, invoices, name):
        Sale = Pool().get('sale.sale')
        with Transaction().set_user(0, set_context=True):
            sales = Sale.search([
                    ('invoices', 'in', [i.id for i in invoices]),
                    ])

        recreated = tuple(i for p in sales for i in p.invoices_recreated)
        ignored = tuple(i for p in sales for i in p.invoices_ignored)

        states = {}
        for invoice in invoices:
            states[invoice.id] = ''
            if invoice in recreated:
                states[invoice.id] = 'recreated'
            elif invoice.id in ignored:
                states[invoice.id] = 'ignored'
        return states

    @classmethod
    def copy(cls, invoices, default=None):
        if default is None:
            default = {}
        default = default.copy()
        default.setdefault('sales', None)
        return super(Invoice, cls).copy(invoices, default=default)

    @classmethod
    def delete(cls, invoices):
        if invoices:
            Transaction().cursor.execute('SELECT id FROM sale_invoices_rel '
                'WHERE invoice IN (' + ','.join(('%s',) * len(invoices)) + ')',
                [i.id for i in invoices])
            if Transaction().cursor.fetchone():
                cls.raise_user_error('delete_sale_invoice')
        super(Invoice, cls).delete(invoices)

    @classmethod
    def paid(cls, invoices):
        pool = Pool()
        Sale = pool.get('sale.sale')
        super(Invoice, cls).paid(invoices)
        with Transaction().set_user(0, set_context=True):
            Sale.process([s for i in cls.browse(invoices) for s in i.sales])

    @classmethod
    def cancel(cls, invoices):
        pool = Pool()
        Sale = pool.get('sale.sale')
        super(Invoice, cls).cancel(invoices)
        with Transaction().set_user(0, set_context=True):
            Sale.process([s for i in cls.browse(invoices) for s in i.sales])

    @classmethod
    @Workflow.transition('draft')
    def draft(cls, invoices):
        Sale = Pool().get('sale.sale')
        with Transaction().set_user(0, set_context=True):
            sales = Sale.search([
                    ('invoices', 'in', [i.id for i in invoices]),
                    ])
        if sales and any(i.state == 'cancel' for i in invoices):
            cls.raise_user_error('reset_invoice_sale')

        return super(Invoice, cls).draft(invoices)


class InvoiceLine:
    __name__ = 'account.invoice.line'

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().cursor

        super(InvoiceLine, cls).__register__(module_name)

        # Migration from 2.6: remove sale_lines
        rel_table = 'sale_line_invoice_lines_rel'
        if TableHandler.table_exist(cursor, rel_table):
            cursor.execute('SELECT sale_line, invoice_line '
                'FROM "' + rel_table + '"')
            for sale_line, invoice_line in cursor.fetchall():
                cursor.execute('UPDATE "' + cls._table + '" '
                    'SET origin = %s '
                    'WHERE id = %s',
                    ('sale.line,%s' % sale_line, invoice_line))
            TableHandler.drop_table(cursor,
                'sale.line-account.invoice.line', rel_table)

    @classmethod
    def _get_origin(cls):
        models = super(InvoiceLine, cls)._get_origin()
        models.append('sale.line')
        return models
