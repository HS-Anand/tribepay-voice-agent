from services.profile_service import get_profile


def profile_tool(client):
    return get_profile(client)
