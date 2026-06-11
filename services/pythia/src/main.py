"""Pythia — lead oracle FastAPI app."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from models import HealthResponse
from runner import run_pipeline

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
