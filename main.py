import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app_state import tribepay_client, auth_service, agent_service

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not tribepay_client.is_authenticated():
        phone = os.getenv("TRIBEPAY_PHONE")
        password = os.getenv("TRIBEPAY_PASSWORD")
        if phone and password:
            auth_service.login(phone, password)
    yield


app = FastAPI(title="TribePay Voice", lifespan=lifespan)


class Query(BaseModel):
    text: str


class LoginBody(BaseModel):
    phone_number: str
    password: str


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/api/health")
def health():
    return {
        "authenticated": tribepay_client.is_authenticated(),
        "username": tribepay_client.username if tribepay_client.is_authenticated() else None,
    }


@app.post("/api/auth/login")
def login(body: LoginBody):
    try:
        auth_service.login(body.phone_number, body.password)
        return {
            "authenticated": True,
            "username": tribepay_client.username,
        }
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/api/agent/query")
def agent_query(query: Query):
    if not tribepay_client.is_authenticated():
        raise HTTPException(status_code=401, detail="Authenticate with TribePay first.")

    try:
        return {"text": agent_service.ask(query.text.strip())}
    except Exception as exc:
        return {"text": f"I couldn't complete that request: {exc}"}


@app.post("/api/agent/reset")
def reset_agent():
    agent_service.pending = None
    return {"reset": True}
