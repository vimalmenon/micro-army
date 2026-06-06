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
        mock_dynamo_client.list_tables.return_value = ["vimal", "other"]
        resp = client.get("/tables")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"tables": ["vimal", "other"]}

    def test_empty(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.list_tables.return_value = []
        resp = client.get("/tables")
        assert resp.json() == {"tables": []}


class TestGetItem:
    def test_found(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = {"app": "user", "id": "abc", "name": "test"}
        resp = client.get("/vimal/item/user")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"item": {"app": "user", "id": "abc", "name": "test"}}

    def test_not_found(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = None
        resp = client.get("/vimal/item/missing")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"].lower()

    def test_with_id(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.get_item.return_value = {"app": "message", "id": "xyz", "data": "val"}
        resp = client.get("/vimal/item/message?id=xyz")
        assert resp.status_code == status.HTTP_200_OK
        # Verify the mock was called with the correct key including id
        mock_dynamo_client.get_item.assert_called_with("vimal", {"app": "message", "id": "xyz"})


class TestPutItem:
    def test_creates_item(self, client, mock_dynamo_client: MagicMock):
        item = {"app": "message", "id": "abc", "name": "new-item"}
        mock_dynamo_client.put_item.return_value = item
        resp = client.post("/vimal/item", json=item)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"item": item}

    def test_put_returns_saved_item(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.put_item.return_value = {"app": "message", "id": "1", "value": "saved"}
        resp = client.post("/vimal/item", json={"app": "message", "id": "1", "value": "sent"})
        assert resp.json() == {"item": {"app": "message", "id": "1", "value": "saved"}}


class TestUpdateItem:
    def test_updates_item(self, client, mock_dynamo_client: MagicMock):
        body = {
            "key": {"app": "message"},
            "update_expression": "SET #n = :v",
            "expression_attr_values": {":v": "updated"},
            "expression_attr_names": {"#n": "name"},
        }
        mock_dynamo_client.update_item.return_value = {"app": "message", "name": "updated"}
        resp = client.put("/vimal/item", json=body)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"item": {"app": "message", "name": "updated"}}

    def test_update_not_found(self, client, mock_dynamo_client: MagicMock):
        body = {
            "key": {"app": "missing"},
            "update_expression": "SET data = :v",
            "expression_attr_values": {":v": "x"},
        }
        mock_dynamo_client.update_item.return_value = None
        resp = client.put("/vimal/item", json=body)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_update_invalid_body(self, client):
        """Missing required fields should return 422."""
        resp = client.put("/vimal/item", json={"key": {"app": "message"}})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteItem:
    def test_deletes_item(self, client):
        resp = client.delete("/vimal/item/message")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"deleted": True}

    def test_delete_with_id(self, client, mock_dynamo_client: MagicMock):
        client.delete("/vimal/item/message?id=xyz")
        mock_dynamo_client.delete_item.assert_called_with("vimal", {"app": "message", "id": "xyz"})

    def test_delete_no_id(self, client, mock_dynamo_client: MagicMock):
        client.delete("/vimal/item/message")
        mock_dynamo_client.delete_item.assert_called_with("vimal", {"app": "message"})


class TestQuery:
    def test_query_items(self, client, mock_dynamo_client: MagicMock):
        items = [{"app": "message", "id": "a"}, {"app": "message", "id": "b"}]
        mock_dynamo_client.query.return_value = items
        body = {
            "key_condition_expression": "app = :app",
            "expression_attr_values": {":app": "message"},
            "limit": 10,
        }
        resp = client.post("/vimal/query", json=body)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"items": items, "count": 2}

    def test_query_empty(self, client, mock_dynamo_client: MagicMock):
        mock_dynamo_client.query.return_value = []
        body = {
            "key_condition_expression": "app = :app",
            "expression_attr_values": {":app": "nonexistent"},
        }
        resp = client.post("/vimal/query", json=body)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"items": [], "count": 0}

    def test_query_with_index(self, client, mock_dynamo_client: MagicMock):
        body = {
            "key_condition_expression": "gsi_pk = :pk",
            "expression_attr_values": {":pk": "abc"},
            "index_name": "gsi1",
        }
        resp = client.post("/vimal/query", json=body)
        assert resp.status_code == status.HTTP_200_OK
        # Verify parameters passed correctly
        mock_dynamo_client.query.assert_called_with(
            "vimal",
            key_condition_expression="gsi_pk = :pk",
            expression_attr_values={":pk": "abc"},
            expression_attr_names=None,
            filter_expression=None,
            index_name="gsi1",
            limit=None,
        )

    def test_query_invalid_body(self, client):
        """Missing required key_condition_expression."""
        resp = client.post("/vimal/query", json={})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestScan:
    def test_scan_all(self, client, mock_dynamo_client: MagicMock):
        items = [{"app": "a"}, {"app": "b"}, {"app": "c"}]
        mock_dynamo_client.scan.return_value = items
        resp = client.post("/vimal/scan", json={})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"items": items, "count": 3}

    def test_scan_with_filter(self, client, mock_dynamo_client: MagicMock):
        items = [{"app": "b"}]
        mock_dynamo_client.scan.return_value = items
        body = {
            "filter_expression": "app = :app",
            "expression_attr_values": {":app": "b"},
        }
        resp = client.post("/vimal/scan", json=body)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == {"items": items, "count": 1}
