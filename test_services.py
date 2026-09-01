"""
Manual service smoke tests.

Run after putting valid TribePay credentials in .env:

    python test_services.py

This checks that the existing backend is reachable and that the service
layer can retrieve profile, wallet balance, transactions, groups,
invoices, and settlement previews. It does not execute money-moving actions.
"""

import os
from dotenv import load_dotenv

from tribepay_client.client import TribePayClient
from services.auth_service import AuthService
from services.profile_service import get_profile
from services.wallet_service import get_wallet_balance
from services.transaction_service import query_transactions
from services.group_service import list_groups, group_members, group_spending
from services.invoice_service import find_invoice, list_pending_invoices
from services.settlement_service import settlement_preview


load_dotenv()

base_url = os.getenv(
    "TRIBEPAY_BASE_URL",
    "https://tribepay-backend.onrender.com",
)
phone = os.getenv("TRIBEPAY_PHONE")
password = os.getenv("TRIBEPAY_PASSWORD")

if not phone or not password:
    raise RuntimeError(
        "Set TRIBEPAY_PHONE and TRIBEPAY_PASSWORD in .env for this smoke test."
    )

client = TribePayClient(base_url)
AuthService(client).login(phone, password)

print("Authenticated:", client.is_authenticated())
print("Profile:", get_profile(client))
print("Wallet:", get_wallet_balance(client))
print("Transactions:", query_transactions(client)["count"])
print("Groups:", list_groups(client))
print("Pending invoices:", list_pending_invoices(client))
print("Invoices:", find_invoice(client))
print("Settlement previews:", settlement_preview(client))

groups = list_groups(client)["groups"]
if groups:
    name = groups[0].get("group_name")
    print(f"Members of '{name}':", group_members(client, name))
    print(f"Spending in '{name}':", group_spending(client, name))
