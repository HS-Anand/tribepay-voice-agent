from services.group_service import list_groups, group_spending, group_members


def list_groups_tool(client):
    return list_groups(client)


def group_spending_tool(client, **kwargs):
    return group_spending(client, **kwargs)


def group_members_tool(client, **kwargs):
    return group_members(client, **kwargs)
