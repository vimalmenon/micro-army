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

    # Gold and other non-equity positions carry quantities that are not "shares"
    # (500 grams of bullion), so the UI needs a label for the quantity cell.
    unit: str = "shares"

    # Optional purchase price per unit. Present only where the cost basis is
    # actually known; the UI leaves the cost/return columns blank otherwise
    # rather than inventing a basis for holdings we have no purchase price for.
    cost_basis: float | None = None
    total_return: float | None = None
    total_return_pct: float | None = None


class PortfolioResponse(BaseModel):
    """Response for the portfolio endpoint."""
    holdings: list[PortfolioHolding]
    total_value: float
    total_pnl: float
    updated_at: str
    market_open: bool | None = None
