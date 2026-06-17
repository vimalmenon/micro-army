from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str = "hestia"
    status: str = "healthy"


# ─── Messages ────────────────────────────────

class MessageDetail(BaseModel):
    id: str
    app: str
    name: str
    email: str
    message: str
    read: bool = False
    created_at: str


class MessageListResponse(BaseModel):
    messages: list[MessageDetail]
    count: int


class MessageUpdateResponse(BaseModel):
    id: str
    read: bool


class MessageDeleteResponse(BaseModel):
    id: str


# ─── Portfolio ───────────────────────────────

class PortfolioHolding(BaseModel):
    """A single holding in the stock portfolio."""
    ticker: str
    name: str
    shares: float
    price: float
    change_pct: float
    change_dollar: float
    total_value: float
    total_pnl: float


class PortfolioResponse(BaseModel):
    """Response for the portfolio endpoint."""
    holdings: list[PortfolioHolding]
    total_value: float
    total_pnl: float
    updated_at: str
    market_open: bool | None = None
