import httpx


class TribePayClient:
    """Thin authenticated HTTP client for the existing TribePay backend."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.access_token = None
        self.refresh_token = None
        self.user = None

    def login(self, phone_number: str, password: str):
        response = httpx.post(
            f"{self.base_url}/api/auth/login/",
            json={
                "phone_number": phone_number,
                "password": password,
            },
            timeout=120.0,
        )
        response.raise_for_status()

        data = response.json()
        self.access_token = data["access"]
        self.refresh_token = data.get("refresh")
        self.user = self.get_me()
        return data

    def is_authenticated(self):
        return bool(self.access_token and self.user)

    @property
    def username(self):
        if not self.user:
            raise RuntimeError("TribePay client is not authenticated.")

        first = str(self.user["first_name"]).lower()
        last = str(self.user["last_name"]).lower()
        phone = str(self.user["phone_number"])

        return f"{first}_{last}_{phone}"

    @property
    def user_id(self):
        if not self.user:
            raise RuntimeError("TribePay client is not authenticated.")
        return self.user["user_id"]

    def _headers(self):
        if not self.access_token:
            raise RuntimeError("TribePay client is not authenticated.")
        return {
            "Authorization": f"Bearer {self.access_token}",
        }

    def get(self, path: str, params=None):
        response = httpx.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()

    def post(self, path: str, json=None):
        response = httpx.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json,
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()

    def patch(self, path: str, json=None):
        response = httpx.patch(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json,
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()

    def get_me(self):
        return self.get("/api/auth/me/")
