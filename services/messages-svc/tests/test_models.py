"""Tests for Pydantic models used in messages-svc."""

import json

import pydantic
import pytest

from models import CreateMessageRequest, HealthResponse, MessageResponse


class TestHealthResponse:
    def test_defaults(self):
        resp = HealthResponse()
        assert resp.status == "ok"
        assert resp.service == "messages-svc"

    def test_serialization(self):
        data = json.loads(HealthResponse().model_dump_json())
        assert data == {"status": "ok", "service": "messages-svc"}


class TestCreateMessageRequest:
    def test_valid(self):
        req = CreateMessageRequest(
            name="Alice",
            email="alice@example.com",
            subject="Hello",
            message="Test body",
        )
        assert req.name == "Alice"
        assert req.email == "alice@example.com"

    def test_invalid_email(self):
        with pytest.raises(pydantic.ValidationError):
            CreateMessageRequest(
                name="Bad",
                email="not-an-email",
                subject="Test",
                message="Body",
            )

    def test_missing_field(self):
        with pytest.raises(pydantic.ValidationError):
            CreateMessageRequest(name="Incomplete", email="a@b.com", subject="Hi")


class TestMessageResponse:
    def test_defaults(self):
        resp = MessageResponse(id="abc-123")
        assert resp.id == "abc-123"
        assert resp.status == "submitted"

    def test_serialization(self):
        data = json.loads(MessageResponse(id="abc-123").model_dump_json())
        assert data == {"id": "abc-123", "status": "submitted"}
