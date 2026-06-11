"""Pythia — lead oracle FastAPI app."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import HealthResponse, LeadStateUpdate
from runner import run_pipeline
from store import get_lead, list_leads, update_lead_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pythia")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting pythia...")
    yield
    logger.info("Shutting down pythia...")


app = FastAPI(
    title="pythia",
    description="Lead oracle — collect, score, enrich, and manage business leads",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow Helios admin dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://admin.completeautomate.com",
    ],
    allow_methods=["GET", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=600,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@app.post("/run")
async def run():
    """Manually trigger the lead pipeline."""
    stats = await run_pipeline()
    return stats


@app.get("/leads")
async def list_all_leads(limit: int = 100):
    """List all leads, newest first."""
    leads = await list_leads(limit=limit)
    return {"leads": leads, "count": len(leads)}


@app.get("/leads/{lead_id}")
async def get_lead_by_id(lead_id: str):
    """Get a single lead by ID."""
    lead = await get_lead(lead_id)
    if not lead:
        return {"error": "Lead not found"}, 404
    return lead


@app.patch("/leads/{lead_id}")
async def update_state(lead_id: str, body: LeadStateUpdate):
    """Update a lead's state (e.g. contacted, qualified, won, not_interested).
    Appends the transition to the lead's history automatically."""
    success = await update_lead_state(lead_id, body.state)
    if not success:
        return {"success": False, "error": "Lead not found or update failed"}
    return {"success": True, "lead_id": lead_id, "state": body.state}
