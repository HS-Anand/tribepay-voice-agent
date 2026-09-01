# TribePay Voice

An agentic voice-and-text assistant over the existing TribePay backend, powered by Groq tool calling.

## Architecture

```
Browser (speech or text)
  -> FastAPI /api/agent/query
  -> Groq LLM
  -> JSON-schema tools
  -> service layer
  -> TribePay HTTP client
  -> TribePay REST API
  -> structured result
  -> LLM natural-language response
  -> browser speech
```

The LLM never calls TribePay directly. Tools call services, and services call the HTTP client.

## Agent capabilities

### Profile and wallet
- Show profile (name, phone, username)
- Personal wallet balance
- Group wallet balances

### Transactions
- Money received / sent
- Spending by date, month, or custom range
- Filter by person, amount, or transaction type
- Resolve people by name, username, or phone number

### Groups
- List groups
- Group spending and transactions
- Group members
- Group-name ambiguity handling

### Invoices
- Count and list pending cash invoices
- Find invoices by counterparty, status, or invoice ID
- Pay an invoice after explicit confirmation
- Reject an invoice after explicit confirmation

### Settlements
- Preview settlement with one person or all counterparties
- Execute settlement after explicit confirmation

## Setup

```bash
cd "tribepay_voice_final 3"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put your Groq API key in `.env`:

```env
GROQ_API_KEY=your_key
GROQ_MODEL=openai/gpt-oss-120b
TRIBEPAY_BASE_URL=https://tribepay-backend.onrender.com
```

Optional env login for startup smoke tests:

```env
TRIBEPAY_PHONE=your_phone
TRIBEPAY_PASSWORD=your_password
```

## Run

Terminal chat:

```bash
python test_agent.py
```

Service smoke tests:

```bash
python test_services.py
```

Browser voice + text UI:

```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`

## Example questions

- Did I pay Raj 500 in June?
- What did I pay this guy between 3 March and 16 March?
- How many cash invoices are pending?
- What is my wallet balance?
- Show my profile
- What groups am I in?
- Who is in the Goa trip group?

For pay, reject, and settle actions, the agent asks for a separate confirmation turn before moving money.

## Project layout

```
main.py                  FastAPI app
app_state.py             Shared client + agent singleton
services/
  agent_service.py       Groq ReAct loop + confirmation handling
  transaction_service.py Transaction history queries
  group_service.py       Group lookups
  invoice_service.py     Invoice search / pay / reject
  settlement_service.py  Settlement preview / execute
  wallet_service.py      Wallet balances
  profile_service.py     User profile
tools/                   Thin wrappers exposed to the LLM
tribepay_client/         Authenticated HTTP client
static/index.html        Voice + text browser UI
test_agent.py            Terminal chat loop
test_services.py         Read-only backend smoke tests
```

## Notes

- Uses the live TribePay backend; no backend changes are required.
- Write actions (pay invoice, reject invoice, execute settlement) require explicit confirmation.
- The agent keeps pending action state in memory for the running process.
