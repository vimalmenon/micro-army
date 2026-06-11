"""Pythia — lead oracle FastAPI app."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from models import HealthResponse, LeadStatusUpdate
from runner import run_pipeline
from store import update_lead_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pythia")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting pythia...")
    yield
    logger.info("Shutting down pythia...")


app = FastAPI(
    title="pythia",
    description="Lead building oracle — collect, score, and surface business leads",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@app.post("/run")
async def run():
    """Manually trigger the lead pipeline."""
    stats = await run_pipeline()
    return stats


@app.patch("/leads/{lead_id}")
async def update_status(lead_id: str, body: LeadStatusUpdate):
    """Update a lead's status (e.g. contacted, not_interested, qualified)."""
    success = await update_lead_status(lead_id, body.status)
    if not success:
        return {"success": False, "error": "Lead not found or update failed"}
    return {"success": True, "lead_id": lead_id, "status": body.status}
