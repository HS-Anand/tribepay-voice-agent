from getpass import getpass
from tribepay_client.client import TribePayClient
from services.auth_service import AuthService
from services.agent_service import AgentService

client = TribePayClient("https://tribepay-backend.onrender.com")
phone = input("TribePay phone number: ")
password = getpass("TribePay password: ")
AuthService(client).login(phone, password)
print("Authenticated:", client.is_authenticated())
agent = AgentService(client)
while True:
    q = input("\nAsk TribePay: ").strip()
    if q.lower() in {"exit", "quit"}: break
    try:
        print("\nAgent:", agent.ask(q))
    except Exception as e:
        print("\nError:", e)
