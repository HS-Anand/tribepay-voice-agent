from tribepay_client.client import TribePayClient
from services.transaction_service import get_all_transactions, resolve_person
from services.invoice_service import get_invoices


def _settlement_counterparties(client):
    """Collect usernames the user may need to settle with from pending expense invoices."""
    invoices = get_invoices(client)
    me = client.username
    counterparties = set()

    for invoice in invoices:
        if str(invoice.get("status", "")).upper() != "PENDING":
            continue
        if str(invoice.get("invoice_type", "")).upper() != "EXPENSE":
            continue

        created_by = str(invoice.get("created_by", ""))
        payer = str(invoice.get("payer", ""))

        if payer == me and created_by and created_by != me:
            counterparties.add(created_by)
        elif created_by == me and payer and payer != me:
            counterparties.add(payer)

    if counterparties:
        return sorted(counterparties)

    transactions = get_all_transactions(client)
    for transaction in transactions:
        if transaction.get("status") != "SUCCESS":
            continue
        for key in ("sender_username", "receiver_username"):
            username = transaction.get(key)
            if username and username != me:
                counterparties.add(username)

    return sorted(counterparties)


def _preview_with_username(client, username):
    return client.get(
        "/settlements/preview/",
        params={"username": username},
    )


def settlement_preview(client, person=None):
    if person:
        transactions = get_all_transactions(client)
        resolved = resolve_person(transactions, person)
        if isinstance(resolved, dict) and "ambiguous" in resolved:
            return {"error": "ambiguous_person", "matches": resolved["ambiguous"]}

        username = resolved or person
        preview = _preview_with_username(client, username)
        if isinstance(preview, dict):
            preview = dict(preview)
            preview["person"] = username
        return preview

    previews = []
    errors = []

    for username in _settlement_counterparties(client):
        try:
            preview = _preview_with_username(client, username)
            if isinstance(preview, dict):
                amount = float(preview.get("amount", 0) or 0)
                direction = str(preview.get("direction", ""))
                if amount > 0 or direction not in {"SETTLED", ""}:
                    previews.append(preview)
        except Exception as exc:
            errors.append({"username": username, "error": str(exc)})

    return {
        "count": len(previews),
        "previews": previews,
        "errors": errors,
    }


def execute_settlement(client, username):
    return client.post("/settlements/execute/", {"username": username})
