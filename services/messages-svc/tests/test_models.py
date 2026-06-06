"""Tests for Pydantic models used in messages-svc."""

import json

from models import (
    CreateMessageRequest,
    DeleteResponse,
    HealthResponse,
    MessageListResponse,
    MessageResponse,
    UpdateMessageRequest,
)


class TestHealthResponse:
    def test_defaults(self):
        resp = HealthResponse()
        assert resp.status == "ok"
        assert resp.service == "messages-svc"

    def test_serialization(self):
        resp = HealthResponse()
        data = json.loads(resp.model_dump_json())
        assert data == {"status": "ok", "service": "messages-svc"}


class TestCreateMessageRequest:
    def test_valid(self):
        req = CreateMessageRequest(
            name="Alice",
            email="alice@example.com",
            subject="Hello",
            message="Test message body",
        )
        assert req.name == "Alice"
        assert req.email == "alice@example.com"

    def test_invalid_email(self):
        import pydantic

        try:
            CreateMessageRequest(
                name="Bad",
                email="not-an-email",
                subject="Test",
                message="Body",
            )
            assert False, "Should have raised"
        except pydantic.ValidationError:
            pass


class TestUpdateMessageRequest:
    def test_mark_read(self):
        req = UpdateMessageRequest(read=True)
        assert req.read is True
        assert req.subject is None

    def test_update_subject(self):
        req = UpdateMessageRequest(subject="New subject")
        assert req.subject == "New subject"
        assert req.read is None

    def test_empty(self):
        req = UpdateMessageRequest()
        assert req.read is None
        assert req.subject is None


class TestMessageResponse:
    def test_with_message(self):
        resp = MessageResponse(message={"id": "abc", "name": "Test"})
        assert resp.message["id"] == "abc"


class TestMessageListResponse:
    def test_empty(self):
        resp = MessageListResponse(messages=[], count=0)
        assert resp.messages == []
        assert resp.count == 0

    def test_with_items(self):
        items = [{"id": "a"}, {"id": "b"}]
        resp = MessageListResponse(messages=items, count=2)
        assert resp.count == 2


class TestDeleteResponse:
    def test_deleted(self):
        resp = DeleteResponse(deleted=True)
        data = json.loads(resp.model_dump_json())
        assert data == {"deleted": True}
