"""Sloth Agent FastAPI Sidecar — MVP Iter-2."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from .database import init_db
from .routers import agent_templates, chat, inspirations, llm
from .services.agent import AgentService
from .services.llm import seed_default_llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await AgentService.seed_lead_agent()
    await seed_default_llm()
    yield


app = FastAPI(title="Sloth Agent Backend", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inspirations.router)
app.include_router(llm.router)
app.include_router(agent_templates.router)
app.include_router(chat.router)


class EchoRequest(BaseModel):
    message: str


class EchoResponse(BaseModel):
    echo: str


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/echo", response_model=EchoResponse)
async def echo(req: EchoRequest):
    return EchoResponse(echo=f"Backend received: {req.message}")
