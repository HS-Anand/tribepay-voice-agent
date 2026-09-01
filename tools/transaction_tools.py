from services.transaction_service import query_transactions


def transaction_tool(client, **kwargs):
    return query_transactions(client, **kwargs)
