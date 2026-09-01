from datetime import date, datetime
from tribepay_client.client import TribePayClient


def _results(data):
    if isinstance(data, dict):
        return data.get("results", data)
    return data


def get_groups(client: TribePayClient):
    return _results(client.get("/wallets/groups/"))


def list_groups(client: TribePayClient):
    groups = get_groups(client)
    return {"count": len(groups), "groups": groups}


def resolve_group(client, group_name):
    groups = get_groups(client)
    query = str(group_name).strip().lower()

    exact = [
        g for g in groups
        if str(g.get("group_name", "")).lower() == query
    ]
    if len(exact) == 1:
        return exact[0]

    matches = [
        g for g in groups
        if query in str(g.get("group_name", "")).lower()
    ]

    if not matches:
        return {
            "error": "group_not_found",
            "message": f"No group found matching '{group_name}'.",
        }

    if len(matches) > 1:
        return {
            "error": "ambiguous_group",
            "matches": [
                {"wid": g.get("wid"), "group_name": g.get("group_name")}
                for g in matches
            ],
        }

    return matches[0]


def _as_date(value):
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def group_spending(client, group_name, start_date=None, end_date=None):
    group = resolve_group(client, group_name)
    if isinstance(group, dict) and "error" in group:
        return group

    start_date = _as_date(start_date)
    end_date = _as_date(end_date)

    data = client.get(
        f"/wallets/group/{group['wid']}/transactions/"
    )
    transactions = _results(data)

    filtered = []

    for transaction in transactions:
        created_at = transaction.get("created_at")
        if created_at:
            transaction_date = datetime.fromisoformat(
                str(created_at).replace("Z", "+00:00")
            ).date()

            if start_date and transaction_date < start_date:
                continue
            if end_date and transaction_date > end_date:
                continue

        filtered.append(transaction)

    return {
        "group_name": group.get("group_name"),
        "count": len(filtered),
        "total_amount": sum(
            float(t.get("amount", 0)) for t in filtered
        ),
        "transactions": filtered,
    }


def group_members(client, group_name):
    group = resolve_group(client, group_name)
    if isinstance(group, dict) and "error" in group:
        return group

    data = client.get(
        f"/wallets/group/{group['wid']}/members/"
    )
    members = _results(data)

    return {
        "group_name": group.get("group_name"),
        "count": len(members),
        "members": members,
    }
