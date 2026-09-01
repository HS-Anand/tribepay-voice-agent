from services.transaction_service import get_all_transactions, resolve_person
from tribepay_client.client import TribePayClient


def _results(data):
    if isinstance(data, dict):
        return data.get("results", data)
    return data


def get_invoices(client: TribePayClient, role=None, status=None):
    params = {}
    if role:
        params["role"] = role
    if status:
        params["status"] = status

    if params:
        return _results(client.get("/invoices/", params=params))
    return _results(client.get("/invoices/"))


def _flatten_values(value):
    values = []

    if isinstance(value, dict):
        for item in value.values():
            values.extend(_flatten_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_flatten_values(item))
    elif isinstance(value, (str, int, float)):
        values.append(str(value).lower())

    return values


def _invoice_id(invoice):
    return invoice.get("iid", invoice.get("id", invoice.get("invoice_id")))


def _person_matches(invoice, person):
    if not person:
        return True

    query = str(person).strip().lower()
    return any(query in value for value in _flatten_values(invoice))


def list_pending_invoices(client, role="payer"):
    invoices = get_invoices(client, role=role, status="PENDING")
    total = sum(float(i.get("amount", 0)) for i in invoices)

    return {
        "count": len(invoices),
        "total_amount": total,
        "role": role,
        "invoices": invoices,
    }


def find_invoice(client, person=None, invoice_id=None, status=None, role=None):
    invoices = get_invoices(client, role=role, status=status)

    if invoice_id:
        matches = [
            invoice
            for invoice in invoices
            if str(_invoice_id(invoice)) == str(invoice_id)
        ]
    elif person:
        matches = [
            invoice
            for invoice in invoices
            if _person_matches(invoice, person)
        ]

        if not matches:
            transactions = get_all_transactions(client)
            resolved = resolve_person(transactions, person)

            if isinstance(resolved, dict) and "ambiguous" in resolved:
                return {
                    "error": "ambiguous_person",
                    "matches": resolved["ambiguous"],
                }

            if isinstance(resolved, str):
                matches = [
                    invoice
                    for invoice in invoices
                    if _person_matches(invoice, resolved)
                ]
    else:
        matches = invoices

    return {
        "count": len(matches),
        "invoices": matches,
        "message": (
            "No matching invoice found."
            if not matches
            else f"Found {len(matches)} matching invoice(s)."
        ),
    }


def pay_invoice(client, invoice_id):
    return client.post(
        "/invoices/pay/",
        {"invoice_id": invoice_id},
    )


def reject_invoice(client, invoice_id):
    return client.post(
        "/invoices/reject/",
        {"invoice_id": invoice_id},
    )
