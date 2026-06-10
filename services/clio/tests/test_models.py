"""Tests for Pydantic models used in clio."""

import json

from models import (
    DeleteResponse,
    HealthResponse,
    ItemListResponse,
    ItemResponse,
    QueryRequest,
    ScanRequest,
    UpdateRequest,
)


class TestHealthResponse:
    def test_defaults(self):
        resp = HealthResponse()
        assert resp.status == "ok"
        assert resp.service == "clio"

    def test_custom_values(self):
        resp = HealthResponse(status="degraded", service="custom")
        assert resp.status == "degraded"
        assert resp.service == "custom"

    def test_serialization(self):
        resp = HealthResponse()
        data = json.loads(resp.model_dump_json())
        assert data == {"status": "ok", "service": "clio"}


class TestItemResponse:
    def test_with_item(self):
        resp = ItemResponse(item={"pk": "abc", "name": "test"})
        assert resp.item == {"pk": "abc", "name": "test"}

    def test_none_item(self):
        resp = ItemResponse()
        assert resp.item is None


class TestItemListResponse:
    def test_empty(self):
        resp = ItemListResponse(items=[], count=0)
        assert resp.items == []
        assert resp.count == 0

    def test_with_items(self):
        items = [{"pk": "a"}, {"pk": "b"}]
        resp = ItemListResponse(items=items, count=2)
        assert resp.items == items
        assert resp.count == 2


class TestQueryRequest:
    def test_minimal(self):
        req = QueryRequest(
            key_condition_expression="pk = :pk",
            expression_attr_values={":pk": "abc"},
        )
        assert req.key_condition_expression == "pk = :pk"
        assert req.expression_attr_values == {":pk": "abc"}
        assert req.expression_attr_names is None
        assert req.filter_expression is None
        assert req.index_name is None
        assert req.limit is None

    def test_full(self):
        req = QueryRequest(
            key_condition_expression="pk = :pk AND begins_with(sk, :prefix)",
            expression_attr_values={":pk": "abc", ":prefix": "2024"},
            expression_attr_names={"#pk": "pk"},
            filter_expression="#pk <> :exclude",
            index_name="gsi1",
            limit=10,
        )
        assert req.index_name == "gsi1"
        assert req.limit == 10
        assert req.filter_expression == "#pk <> :exclude"


class TestScanRequest:
    def test_minimal(self):
        req = ScanRequest()
        assert req.filter_expression is None
        assert req.limit is None

    def test_with_filter(self):
        req = ScanRequest(
            filter_expression="age > :age",
            expression_attr_values={":age": 21},
            limit=50,
        )
        assert req.filter_expression == "age > :age"
        assert req.limit == 50


class TestUpdateRequest:
    def test_minimal(self):
        req = UpdateRequest(
            key={"pk": "abc"},
            update_expression="SET #n = :v",
            expression_attr_values={":v": "new"},
            expression_attr_names={"#n": "name"},
        )
        assert req.key == {"pk": "abc"}
        assert req.update_expression == "SET #n = :v"
        assert req.expression_attr_names == {"#n": "name"}

    def test_no_attr_names(self):
        req = UpdateRequest(
            key={"pk": "abc"},
            update_expression="SET data = :v",
            expression_attr_values={":v": "val"},
        )
        assert req.expression_attr_names is None


class TestDeleteResponse:
    def test_deleted_true(self):
        resp = DeleteResponse(deleted=True)
        assert resp.deleted is True

    def test_deleted_false(self):
        resp = DeleteResponse(deleted=False)
        assert resp.deleted is False

    def test_serialization(self):
        resp = DeleteResponse(deleted=True)
        data = json.loads(resp.model_dump_json())
        assert data == {"deleted": True}
