import json
import os
import re

from dotenv import load_dotenv
from groq import Groq
import httpx

from tools.transaction_tools import transaction_tool
from tools.group_tools import (
    list_groups_tool,
    group_spending_tool,
    group_members_tool,
)
from tools.invoice_tools import (
    find_invoice_tool,
    list_pending_invoices_tool,
    pay_invoice_tool,
    reject_invoice_tool,
)
from tools.settlement_tools import (
    settlement_preview_tool,
    execute_settlement_tool,
)
from tools.wallet_tools import wallet_balance_tool
from tools.profile_tools import profile_tool

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_TOOL_ROUNDS = 8


def _function_tool(name, description, properties=None, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
            },
        },
    }


TOOLS = [
    _function_tool(
        "get_profile",
        "Get the authenticated user's TribePay profile: name, phone, username.",
    ),
    _function_tool(
        "get_wallet_balance",
        "Get the authenticated user's personal wallet balance and group wallet balances.",
    ),
    _function_tool(
        "transaction_tool",
        "Query successful TribePay transactions for money received, money sent, spending, a person, amount, date, month, or transaction type.",
        {
            "start_date": {"type": "string", "description": "Start date, YYYY-MM-DD."},
            "end_date": {"type": "string", "description": "End date, YYYY-MM-DD."},
            "person": {"type": "string", "description": "Person's name, phone number, or username."},
            "amount": {"type": "number", "description": "Exact amount if specified."},
            "transaction_type": {"type": "string", "description": "Transaction type if specified."},
            "direction": {
                "type": "string",
                "enum": ["incoming", "outgoing"],
                "description": "Whether money was received or sent.",
            },
        },
    ),
    _function_tool(
        "list_groups",
        "List all TribePay groups the authenticated user belongs to.",
    ),
    _function_tool(
        "group_spending",
        "Get spending/transactions for a named TribePay group, optionally within a date range.",
        {
            "group_name": {"type": "string", "description": "Group name."},
            "start_date": {"type": "string", "description": "Start date, YYYY-MM-DD."},
            "end_date": {"type": "string", "description": "End date, YYYY-MM-DD."},
        },
        ["group_name"],
    ),
    _function_tool(
        "group_members",
        "List the members of a named TribePay group.",
        {"group_name": {"type": "string", "description": "Group name."}},
        ["group_name"],
    ),
    _function_tool(
        "list_pending_invoices",
        "List pending cash invoices. Use for 'how many invoices are pending' or before paying multiple invoices.",
        {
            "role": {
                "type": "string",
                "enum": ["payer", "creator"],
                "description": "payer = invoices the user must pay; creator = invoices the user created.",
            },
        },
    ),
    _function_tool(
        "find_invoice",
        "Find invoices by counterparty, invoice ID, or status.",
        {
            "person": {"type": "string", "description": "Counterparty name, phone number, or username."},
            "invoice_id": {"type": "string", "description": "Invoice ID if known."},
            "status": {"type": "string", "description": "Invoice status such as PENDING, PAID, REJECTED."},
            "role": {"type": "string", "enum": ["payer", "creator"], "description": "Filter by payer or creator role."},
        },
    ),
    _function_tool(
        "pay_invoice",
        "Pay a specific invoice. Only use after the user explicitly confirmed the exact invoice found in the previous turn.",
        {"invoice_id": {"type": "string", "description": "Invoice ID."}},
        ["invoice_id"],
    ),
    _function_tool(
        "reject_invoice",
        "Reject a specific invoice. Only use after the user explicitly confirmed rejection.",
        {"invoice_id": {"type": "string", "description": "Invoice ID."}},
        ["invoice_id"],
    ),
    _function_tool(
        "settlement_preview",
        "Preview settlement balances. Without a person, returns all settlement previews. With a person, previews settlement with that counterparty.",
        {
            "person": {"type": "string", "description": "Person name, phone number, or username."},
        },
    ),
    _function_tool(
        "execute_settlement",
        "Execute a settlement with the exact username returned by settlement_preview. Only use after explicit confirmation.",
        {"username": {"type": "string", "description": "Exact backend username from the settlement preview."}},
        ["username"],
    ),
]

SYSTEM_PROMPT = """
You are TribePay Voice, a concise financial assistant for the authenticated TribePay user.

You have access to real account data through tools. NEVER invent financial information.

PROFILE AND WALLET
- get_profile for "who am I", profile, name, phone, username.
- get_wallet_balance for wallet balance, how much money I have, personal balance, group balances.

TRANSACTIONS
- Use transaction_tool for money received, money sent, spending, transactions, transaction amounts, people, dates, months, and transaction types.
- Convert natural-language periods such as "in June", "3 March to 16 March", or "last month" into start_date/end_date.
- If the user gives a phone number or name, pass exactly what they said as person.
- If the tool says the person is ambiguous, ask the user to choose. Never guess.

GROUPS
- list_groups for "what groups am I part of?"
- group_spending for spending/transactions in a named group.
- group_members for "who is in [group]?"
- If a group name is ambiguous, ask which group they mean.

INVOICES
- list_pending_invoices for "how many invoices are pending", pending cash invoices, or invoices I need to pay.
- find_invoice to search invoices by person, status, or invoice ID.
- If the user asks to pay/clear an invoice, FIRST use find_invoice or list_pending_invoices.
- Tell the user the counterparty and amount found, then ask for explicit confirmation.
- Do NOT call pay_invoice in the same turn as the original payment request.
- pay_invoice is only allowed after an explicit affirmative confirmation.
- reject_invoice follows the same confirmation rules as pay_invoice.
- To pay multiple pending invoices, list them first, summarize totals, ask for confirmation, then pay each one after confirmation.

SETTLEMENTS
- settlement_preview for settlement status. Pass person when the user names someone.
- Tell the user what the preview says and ask for explicit confirmation before executing.
- execute_settlement is only allowed after an explicit affirmative confirmation.
- can_settle=false means the other person owes you; only execute when you owe them.

RESPONSE STYLE
- Speak naturally; this answer will be read aloud.
- NEVER expose Python dictionaries, JSON, raw API responses, or internal tool names.
- Do not say "the tool returned".
- Use ₹ for TribePay monetary amounts.
- Give the useful answer first.
- Simple questions should normally get 1–3 sentences.
- For lists, use short numbered items.
- If there are no results, say so plainly.
- If an API/tool fails, say the request could not be completed. Do not fabricate an answer.
"""


def _is_affirmative(text):
    value = re.sub(r"[.!?,]+$", "", text.strip().lower())
    return value in {
        "yes", "yeah", "yep", "yup", "confirm", "confirmed",
        "do it", "go ahead", "pay it", "pay that", "pay this",
        "pay the invoice", "pay said invoice", "clear it",
        "clear that", "clear this", "settle it", "settle that",
        "pay now", "execute", "execute it", "settle now",
        "okay", "ok", "sure", "yes pay it", "yeah pay it",
        "reject it", "reject that", "reject the invoice",
    }


def _invoice_id(invoice):
    return invoice.get("iid", invoice.get("invoice_id", invoice.get("id")))


class AgentService:
    def __init__(self, tribepay_client):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is missing from .env")

        self.groq = Groq(api_key=api_key)
        self.tribepay_client = tribepay_client
        self.pending = None

    def _safe_tool(self, func, **kwargs):
        try:
            return func(self.tribepay_client, **kwargs)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            try:
                detail = exc.response.json()
            except ValueError:
                pass
            return {"error": "api_error", "status": exc.response.status_code, "detail": detail}
        except Exception as exc:
            return {"error": "tool_failed", "message": str(exc)}

    def _tool_result(self, name, args):
        if name == "get_profile":
            return self._safe_tool(profile_tool)

        if name == "get_wallet_balance":
            return self._safe_tool(wallet_balance_tool)

        if name == "transaction_tool":
            return self._safe_tool(transaction_tool, **args)

        if name == "list_groups":
            return self._safe_tool(list_groups_tool)

        if name == "group_spending":
            return self._safe_tool(group_spending_tool, **args)

        if name == "group_members":
            return self._safe_tool(group_members_tool, **args)

        if name == "list_pending_invoices":
            return self._safe_tool(
                list_pending_invoices_tool,
                role=args.get("role", "payer"),
            )

        if name == "find_invoice":
            return self._safe_tool(find_invoice_tool, **args)

        if name == "pay_invoice":
            invoice_id = args.get("invoice_id")
            if not self.pending:
                return {"error": "payment_confirmation_required"}

            if (
                self.pending.get("action") != "pay_invoice"
                or str(self.pending.get("invoice_id")) != str(invoice_id)
            ):
                return {"error": "payment_confirmation_required"}

            result = self._safe_tool(pay_invoice_tool, invoice_id=invoice_id)
            self.pending = None
            return result

        if name == "reject_invoice":
            invoice_id = args.get("invoice_id")
            if not self.pending:
                return {"error": "reject_confirmation_required"}

            if (
                self.pending.get("action") != "reject_invoice"
                or str(self.pending.get("invoice_id")) != str(invoice_id)
            ):
                return {"error": "reject_confirmation_required"}

            result = self._safe_tool(reject_invoice_tool, invoice_id=invoice_id)
            self.pending = None
            return result

        if name == "settlement_preview":
            result = self._safe_tool(
                settlement_preview_tool,
                person=args.get("person"),
            )
            if isinstance(result, dict) and not result.get("error"):
                if "previews" in result:
                    settleable = [
                        preview
                        for preview in result["previews"]
                        if preview.get("can_settle")
                    ]
                    if len(settleable) == 1:
                        preview = settleable[0]
                        self.pending = {
                            "action": "execute_settlement",
                            "username": preview.get("user"),
                            "preview": preview,
                        }
                else:
                    username = result.get("person") or result.get("user")
                    if result.get("can_settle"):
                        self.pending = {
                            "action": "execute_settlement",
                            "username": username,
                            "preview": result,
                        }
            return result

        if name == "execute_settlement":
            if not self.pending or self.pending.get("action") != "execute_settlement":
                return {"error": "settlement_confirmation_required"}

            username = self.pending.get("username")
            if not username:
                return {"error": "settlement_confirmation_required"}

            result = self._safe_tool(
                execute_settlement_tool,
                username=username,
            )
            self.pending = None
            return result

        return {"error": f"Unknown tool: {name}"}

    def _finalize(self, messages):
        response = self.groq.chat.completions.create(
            model=MODEL,
            messages=messages,
            tool_choice="none",
            temperature=0.1,
        )
        return response.choices[0].message.content or "I couldn't generate a response."

    def _handle_confirmation(self, question):
        action = self.pending["action"]

        if action == "pay_invoice":
            result = self._tool_result(
                "pay_invoice",
                {"invoice_id": self.pending["invoice_id"]},
            )
        elif action == "reject_invoice":
            result = self._tool_result(
                "reject_invoice",
                {"invoice_id": self.pending["invoice_id"]},
            )
        else:
            result = self._tool_result(
                "execute_settlement",
                {"username": self.pending["username"]},
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    question
                    + "\nThe user is confirming the action identified in the previous turn. "
                    "Report the result naturally and do not ask for an ID again."
                ),
            },
            {
                "role": "tool",
                "tool_call_id": "confirmed_action",
                "content": json.dumps(
                    {"confirmed_action": action, "result": result},
                    default=str,
                ),
            },
        ]
        return self._finalize(messages)

    def _remember_invoice(self, result, action):
        if result.get("count") != 1:
            return

        invoice = result["invoices"][0]
        status = str(invoice.get("status", "")).upper()
        invoice_id = _invoice_id(invoice)

        if not invoice_id or status not in {"PENDING", "UNPAID", ""}:
            return

        self.pending = {
            "action": action,
            "invoice_id": invoice_id,
            "invoice": invoice,
        }

    def _invoice_action(self, question: str):
        lowered = question.lower()
        if any(word in lowered for word in ("reject", "decline", "refuse", "deny")):
            return "reject_invoice"
        return "pay_invoice"

    def ask(self, question: str):
        if self.pending and _is_affirmative(question):
            return self._handle_confirmation(question)

        invoice_action = self._invoice_action(question)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.groq.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1,
            )

            message = response.choices[0].message
            messages.append(message)

            if not message.tool_calls:
                return message.content or "I couldn't generate a response."

            for call in message.tool_calls:
                name = call.function.name
                args = json.loads(call.function.arguments or "{}")
                result = self._tool_result(name, args)

                if name == "find_invoice":
                    self._remember_invoice(result, invoice_action)
                elif name == "list_pending_invoices" and result.get("count") == 1:
                    self._remember_invoice(result, invoice_action)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        return "I couldn't complete that request within the allowed tool steps."
