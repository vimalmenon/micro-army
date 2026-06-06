"""Tests for FastAPI routes — all DynamoDB calls are mocked."""

from unittest.mock import MagicMock

import pytest
from fastapi import status


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data == {"status": "ok", "service": "dynamo-svc"}


class TestListTables:
    def test_returns_tables(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.list_tables.return_value = ["users", "orders"]
        resp = client.get("/tables")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"tables": ["users", "orders"]}

    def test_empty(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.list_tables.return_value = []
        resp = client.get("/tables")
        assert resp.json() == {"tables": []}


class TestGetItem:
    def test_found(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = {"pk": "abc", "name": "test"}
        resp = client.get("/users/item/abc")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"item": {"pk": "abc", "name": "test"}}

    def test_not_found(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = None
        resp = client.get("/users/item/missing")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"].lower()

    def test_with_sk(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = {"pk": "abc", "sk": "xyz", "data": "val"}
        resp = client.get("/users/item/abc?sk=xyz")
        assert resp.status_code == status.HTTP_200_OK
        # Verify the mock was called with the correct key including sk
        mock_dynamo_client.get_item.assert_called_with("users", {"pk": "abc", "sk": "xyz"})


class TestPutItem:
    def test_creates_item(self, client, mock_dynamo_client: MagicMock):
        item = {"pk": "abc", "name": "new-item"}
        mock_dynamo_client.put_item.return_value = item
        resp = client.post("/users/item", json=item)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"item": item}

    def test_put_returns_saved_item(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.put_item.return_value = {"pk": "1", "value": "saved"}
        resp = client.post("/users/item", json={"pk": "1", "value": "sent"})
        assert resp.json() == {"item": {"pk": "1", "value": "saved"}}


class TestUpdateItem:
    def test_updates_item(self, client, mock_dynamo_client: MagicMock):
        body = {
            "key": {"pk": "abc"},
            "update_expression": "SET #n = :v",
            "expression_attr_values": {":v": "updated"},
            "expression_attr_names": {"#n": "name"},
        }
        mock_dynamo_client.update_item.return_value = {"pk": "abc", "name": "updated"}
        resp = client.put("/users/item", json=body)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"item": {"pk": "abc", "name": "updated"}}

    def test_update_not_found(self, client, mock_dynamo_client: MagicMock):
        body = {
            "key": {"pk": "missing"},
            "update_expression": "SET data = :v",
            "expression_attr_values": {":v": "x"},
        }
        mock_dynamo_client.update_item.return_value = None
        resp = client.put("/users/item", json=body)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_update_invalid_body(self, client):
        """Missing required fields should return 422."""
        resp = client.put("/users/item", json={"key": {"pk": "abc"}})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteItem:
    def test_deletes_item(self, client):
        resp = client.delete("/users/item/abc")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"deleted": True}

    def test_delete_with_sk(self, client, mock_dynamo_client: MagicMock):
        client.delete("/users/item/abc?sk=xyz")
        mock_dynamo_client.delete_item.assert_called_with("users", {"pk": "abc", "sk": "xyz"})

    def test_delete_no_sk(self, client, mock_dynamo_client: MagicMock):
        client.delete("/users/item/abc")
        mock_dynamo_client.delete_item.assert_called_with("users", {"pk": "abc"})


class TestQuery:
    def test_query_items(self, client, mock_dynamo_client: MagicMock):
        items = [{"pk": "abc", "sk": "a"}, {"pk": "abc", "sk": "b"}]
        mock_dynamo_client.query.return_value = items
        body = {
            "key_condition_expression": "pk = :pk",
            "expression_attr_values": {":pk": "abc"},
            "limit": 10,
        }
        resp = client.post("/users/query", json=body)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"items": items, "count": 2}

    def test_query_empty(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.query.return_value = []
        body = {
            "key_condition_expression": "pk = :pk",
            "expression_attr_values": {":pk": "nonexistent"},
        }
        resp = client.post("/users/query", json=body)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"items": [], "count": 0}

    def test_query_with_index(self, client, mock_dynamo_client: MagicMock):
        body = {
            "key_condition_expression": "gsi_pk = :pk",
            "expression_attr_values": {":pk": "abc"},
            "index_name": "gsi1",
        }
        resp = client.post("/users/query", json=body)
        assert resp.status_code == status.HTTP_200_OK
        # Verify parameters passed correctly
        mock_dynamo_client.query.assert_called_with(
            "users",
            key_condition_expression="gsi_pk = :pk",
            expression_attr_values={":pk": "abc"},
            expression_attr_names=None,
            filter_expression=None,
            index_name="gsi1",
            limit=None,
        )

    def test_query_invalid_body(self, client):
        """Missing required key_condition_expression."""
        resp = client.post("/users/query", json={})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestScan:
    def test_scan_all(self, client, mock_dynamo_client: MagicMock):
        items = [{"pk": "a"}, {"pk": "b"}, {"pk": "c"}]
        mock_dynamo_client.scan.return_value = items
        resp = client.post("/users/scan", json={})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"items": items, "count": 3}

    def test_scan_with_filter(self, client, mock_dynamo_client: MagicMock):
        items = [{"pk": "b"}]
        mock_dynamo_client.scan.return_value = items
        body = {
            "filter_expression": "pk = :pk",
            "expression_attr_values": {":pk": "b"},
        }
        resp = client.post("/users/scan", json=body)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"items": items, "count": 1}


class TestNoCORS:
    """Internal ClusterIP service — CORS not needed."""

    def test_options_not_allowed(self, client):
        """OPTIONS method should not be handled (no CORSMiddleware)."""
        resp = client.options("/health")
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
