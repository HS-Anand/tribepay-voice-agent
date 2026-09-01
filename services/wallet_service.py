from tribepay_client.client import TribePayClient


def _results(data):
    if isinstance(data, dict):
        return data.get("results", data)
    return data


def get_wallets(client: TribePayClient):
    data = client.get("/wallets/me/")
    wallets = _results(data)
    if isinstance(wallets, dict):
        return [wallets]
    return list(wallets)


def get_wallet_balance(client: TribePayClient):
    wallets = get_wallets(client)

    personal = next(
        (w for w in wallets if str(w.get("wallet_type", "")).upper() == "PRS"),
        None,
    )

    groups = [
        {
            "wid": w.get("wid"),
            "balance": w.get("balance"),
            "group_name": w.get("group_name"),
        }
        for w in wallets
        if str(w.get("wallet_type", "")).upper() == "GRP"
    ]

    return {
        "personal_balance": personal.get("balance") if personal else "0.00",
        "personal_wallet_id": personal.get("wid") if personal else None,
        "group_wallets": groups,
        "total_wallets": len(wallets),
    }


def get_personal_wallet_id(client: TribePayClient):
    balance = get_wallet_balance(client)
    return balance.get("personal_wallet_id")
