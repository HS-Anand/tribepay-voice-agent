from services.wallet_service import get_wallet_balance


def wallet_balance_tool(client):
    return get_wallet_balance(client)
