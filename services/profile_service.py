from tribepay_client.client import TribePayClient


def get_profile(client: TribePayClient):
    user = client.get_me()
    return {
        "user_id": user.get("user_id"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "phone_number": user.get("phone_number"),
        "username": client.username,
    }
