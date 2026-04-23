"""Sloth Agent FastAPI Sidecar - Phase 0 minimal echo endpoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Sloth Agent Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EchoRequest(BaseModel):
    message: str


class EchoResponse(BaseModel):
    echo: str


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/echo", response_model=EchoResponse)
async def echo(req: EchoRequest):
    return EchoResponse(echo=f"Backend received: {req.message}")
