from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "iris"


class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    body_type: str = "html"  # "html" or "plain"
    cc: Optional[list[EmailStr]] = None
    bcc: Optional[list[EmailStr]] = None


class EmailResponse(BaseModel):
    id: str
    to: str
    subject: str
    status: str = "sent"
    sent_at: str = ""


class EmailRecord(BaseModel):
    """Schema for the email record stored in DynamoDB."""
    id: str
    to: str
    subject: str
    body_preview: str  # First 100 chars
    status: str
    sent_at: str
    error: str = ""
