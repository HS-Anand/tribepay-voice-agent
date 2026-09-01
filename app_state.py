import os
from dotenv import load_dotenv
from tribepay_client.client import TribePayClient
from services.auth_service import AuthService
from services.agent_service import AgentService

load_dotenv()
tribepay_client = TribePayClient(os.getenv("TRIBEPAY_BASE_URL", "https://tribepay-backend.onrender.com"))
auth_service = AuthService(tribepay_client)
agent_service = AgentService(tribepay_client)
