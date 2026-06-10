import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Path

from config import settings
from dynamo_client import DynamoClient
from models import (
    DeleteResponse,
    HealthResponse,
    ItemListResponse,
    ItemResponse,
    QueryRequest,
    ScanRequest,
    UpdateRequest,
)
from shared.log_config import setup_logging
from shared.metrics import MetricsMiddleware, metrics_handler

setup_logging("clio")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting clio...")
    DynamoClient()
    yield
    logger.info("Shutting down clio...")


app = FastAPI(
    title="clio",
    description="Amazon DynamoDB gateway microservice",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Prometheus metrics ─────────────────────────
app.add_middleware(MetricsMiddleware)
app.add_route("/metrics", metrics_handler, include_in_schema=False)

dynamo = DynamoClient()


def _build_key(app: str, id: str | None = None) -> dict:
    key: dict = {"app": app}
    if id:
        key["id"] = id
    return key


# ─── Health ────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse()


# ─── CRUD ──────────────────────────────────────────


@app.get("/{table}/item/{app}", response_model=ItemResponse, tags=["items"])
async def get_item(
    table: str = Path(..., description="DynamoDB table name"),
    app: str = Path(..., description="Partition key value (app)"),
    id: str | None = None,
):
    key = _build_key(app, id)
    item = dynamo.get_item(table, key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item with key {key} not found in {table}")
    return ItemResponse(item=item)


@app.post("/{table}/item", response_model=ItemResponse, tags=["items"])
async def put_item(
    table: str,
    item: dict,
):
    result = dynamo.put_item(table, item)
    return ItemResponse(item=result)


@app.put("/{table}/item", response_model=ItemResponse, tags=["items"])
async def update_item(
    table: str,
    body: UpdateRequest,
):
    result = dynamo.update_item(
        table,
        key=body.key,
        update_expression=body.update_expression,
        expression_attr_values=body.expression_attr_values,
        expression_attr_names=body.expression_attr_names,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Item not found in {table}")
    return ItemResponse(item=result)


@app.delete("/{table}/item/{app}", response_model=DeleteResponse, tags=["items"])
async def delete_item(
    table: str,
    app: str,
    id: str | None = None,
):
    key = _build_key(app, id)
    dynamo.delete_item(table, key)
    return DeleteResponse(deleted=True)


# ─── Query / Scan ──────────────────────────────────


@app.post("/{table}/query", response_model=ItemListResponse, tags=["items"])
async def query_items(
    table: str,
    body: QueryRequest,
):
    items = dynamo.query(
        table,
        key_condition_expression=body.key_condition_expression,
        expression_attr_values=body.expression_attr_values,
        expression_attr_names=body.expression_attr_names,
        filter_expression=body.filter_expression,
        index_name=body.index_name,
        limit=body.limit,
    )
    return ItemListResponse(items=items, count=len(items))


@app.post("/{table}/scan", response_model=ItemListResponse, tags=["items"])
async def scan_items(
    table: str,
    body: ScanRequest,
):
    items = dynamo.scan(
        table,
        filter_expression=body.filter_expression,
        expression_attr_values=body.expression_attr_values,
        expression_attr_names=body.expression_attr_names,
        limit=body.limit,
    )
    return ItemListResponse(items=items, count=len(items))
