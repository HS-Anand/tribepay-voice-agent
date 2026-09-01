from datetime import date, datetime
from tribepay_client.client import TribePayClient


def get_all_transactions(client: TribePayClient):
    """Fetch every page of the authenticated user's transaction history."""
    transactions = []
    path = "/api/transactions/history/"

    while path:
        data = client.get(path)

        if isinstance(data, dict):
            transactions.extend(data.get("results", []))
            next_url = data.get("next")
        elif isinstance(data, list):
            transactions.extend(data)
            next_url = None
        else:
            next_url = None

        path = (
            next_url.replace(client.base_url, "")
            if next_url
            else None
        )

    return transactions


def resolve_person(transactions, person):
    """
    Resolve a natural-language person reference against identifiers that
    are actually present in the authenticated user's transaction history.

    Returns:
      - username string when exactly one match exists
      - {"ambiguous": [...]} when multiple matches exist
      - original input when there is no match
    """
    if not person:
        return None

    query = str(person).strip()
    low = query.lower()

    candidates = set()
    for transaction in transactions:
        for key in ("sender_username", "receiver_username"):
            value = transaction.get(key)
            if value:
                candidates.add(str(value))

    # Exact username/identifier match.
    exact = [x for x in candidates if x.lower() == low]
    if exact:
        return exact[0]

    # Phone-number match. This intentionally accepts a phone number supplied
    # by the user without requiring them to know the backend username.
    digits = "".join(c for c in query if c.isdigit())
    if len(digits) >= 10:
        phone_matches = [x for x in candidates if x.endswith(digits)]
        if len(phone_matches) == 1:
            return phone_matches[0]
        if len(phone_matches) > 1:
            return {"ambiguous": sorted(phone_matches)}

    # Name / username substring match.
    name_matches = [x for x in candidates if low in x.lower()]
    if len(name_matches) == 1:
        return name_matches[0]
    if len(name_matches) > 1:
        return {"ambiguous": sorted(name_matches)}

    # No resolution is not permission to guess.
    return query


def _as_date(value):
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def query_transactions(
    client,
    start_date=None,
    end_date=None,
    person=None,
    amount=None,
    transaction_type=None,
    direction=None,
):
    transactions = get_all_transactions(client)

    start_date = _as_date(start_date)
    end_date = _as_date(end_date)

    resolved = resolve_person(transactions, person)
    if isinstance(resolved, dict) and "ambiguous" in resolved:
        return {
            "error": "ambiguous_person",
            "matches": resolved["ambiguous"],
        }

    filtered = []

    for transaction in transactions:
        if transaction.get("status") != "SUCCESS":
            continue

        created_at = transaction.get("created_at")
        if not created_at:
            continue

        transaction_date = datetime.fromisoformat(
            str(created_at).replace("Z", "+00:00")
        ).date()

        if start_date and transaction_date < start_date:
            continue
        if end_date and transaction_date > end_date:
            continue

        sender = transaction.get("sender_username")
        receiver = transaction.get("receiver_username")

        if resolved:
            if direction == "outgoing" and receiver != resolved:
                continue
            if direction == "incoming" and sender != resolved:
                continue
            if direction not in ("incoming", "outgoing"):
                if resolved not in (sender, receiver):
                    continue

        if direction == "outgoing" and sender != client.username:
            continue
        if direction == "incoming" and receiver != client.username:
            continue

        if amount is not None:
            if float(transaction.get("amount", 0)) != float(amount):
                continue

        if transaction_type:
            if str(transaction.get("transaction_type", "")).upper() != str(transaction_type).upper():
                continue

        filtered.append(transaction)

    return {
        "count": len(filtered),
        "total_amount": sum(float(t.get("amount", 0)) for t in filtered),
        "transactions": filtered,
    }
