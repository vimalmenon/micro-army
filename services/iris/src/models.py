from __future__ import annotations

import hashlib
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


# ─── Subscriber models ─────────────────────────


class SubscribeRequest(BaseModel):
    email: EmailStr
    name: str = ""


class UnsubscribeRequest(BaseModel):
    email: EmailStr


class SubscriberResponse(BaseModel):
    email: str
    name: str
    silenced: bool
    subscribed_at: str
    silenced_at: str | None = None


class SubscriberRecord(BaseModel):
    """Schema for subscriber records stored in DynamoDB (CA#Subscriber)."""
    id: str
    email: str
    name: str
    silenced: bool = False
    subscribed_at: str
    silenced_at: str | None = None


def subscriber_id(email: str) -> str:
    """Deterministic ID for a subscriber — MD5 hash of the email."""
    return hashlib.md5(email.lower().encode()).hexdigest()
