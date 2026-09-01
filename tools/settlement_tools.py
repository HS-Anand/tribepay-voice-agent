from services.settlement_service import settlement_preview, execute_settlement


def settlement_preview_tool(client, person=None):
    return settlement_preview(client, person=person)


def execute_settlement_tool(client, username):
    return execute_settlement(client, username=username)
