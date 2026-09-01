class AuthService:
    def __init__(self, client):
        self.client = client

    def login(self, phone_number, password):
        return self.client.login(phone_number, password)

    def is_authenticated(self):
        return self.client.is_authenticated()
