from services.invoice_service import (
    find_invoice,
    pay_invoice,
    reject_invoice,
    list_pending_invoices,
)


def find_invoice_tool(client, **kwargs):
    return find_invoice(client, **kwargs)


def list_pending_invoices_tool(client, role="payer"):
    return list_pending_invoices(client, role=role)


def pay_invoice_tool(client, **kwargs):
    return pay_invoice(client, **kwargs)


def reject_invoice_tool(client, **kwargs):
    return reject_invoice(client, **kwargs)
