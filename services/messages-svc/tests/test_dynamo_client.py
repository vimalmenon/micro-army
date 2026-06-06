"""Tests for DynamoClient — all AWS calls are mocked."""

from unittest.mock import MagicMock, patch

import botocore
import pytest

from dynamo_client import DynamoClient


@pytest.fixture(autouse=True)
def reset_singleton():
    DynamoClient._instance = None
    yield


@pytest.fixture
def mock_boto3():
    with patch("dynamo_client.boto3") as mock_boto3:
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {"app": "message", "id": "abc", "name": "Alice"}}
        mock_table.put_item.return_value = {}
        mock_table.update_item.return_value = {"Attributes": {"app": "message", "id": "abc", "read": True}}
        mock_table.delete_item.return_value = {}
        mock_table.query.return_value = {"Items": [{"app": "message", "id": "q1"}, {"app": "message", "id": "q2"}]}
        mock_table.scan.return_value = {"Items": [{"app": "message", "id": "s1"}, {"app": "message", "id": "s2"}]}

        mock_resource = MagicMock()
        mock_resource.Table.return_value = mock_table
        mock_resource.tables.all.return_value = ["vimal"]

        mock_boto3.resource.return_value = mock_resource

        yield {
            "boto3": mock_boto3,
            "resource": mock_resource,
            "table": mock_table,
        }


class TestSingleton:
    def test_same_instance(self):
        a = DynamoClient()
        b = DynamoClient()
        assert a is b


class TestGetItem:
    def test_found(self, mock_boto3):
        client = DynamoClient()
        result = client.get_item("vimal", {"app": "message", "id": "abc"})
        assert result == {"app": "message", "id": "abc", "name": "Alice"}

    def test_not_found(self, mock_boto3):
        mock_boto3["table"].get_item.return_value = {}
        result = DynamoClient().get_item("vimal", {"app": "missing"})
        assert result is None

    def test_raises_on_error(self, mock_boto3):
        mock_boto3["table"].get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalServerError"}}, "GetItem"
        )
        with pytest.raises(botocore.exceptions.ClientError):
            DynamoClient().get_item("vimal", {"app": "abc"})


class TestPutItem:
    def test_put(self, mock_boto3):
        item = {"app": "message", "id": "new", "name": "Test"}
        result = DynamoClient().put_item("vimal", item)
        assert result == item


class TestUpdateItem:
    def test_update(self, mock_boto3):
        result = DynamoClient().update_item(
            "vimal",
            key={"app": "message", "id": "abc"},
            update_expression="SET #read = :read",
            expression_attr_values={":read": True},
            expression_attr_names={"#read": "read"},
        )
        assert result == {"app": "message", "id": "abc", "read": True}


class TestDeleteItem:
    def test_delete(self, mock_boto3):
        assert DynamoClient().delete_item("vimal", {"app": "message", "id": "abc"}) is True


class TestQuery:
    def test_query(self, mock_boto3):
        result = DynamoClient().query(
            "vimal",
            key_condition_expression="app = :app",
            expression_attr_values={":app": "message"},
            index_name="app-index",
        )
        assert len(result) == 2

    def test_query_pagination(self, mock_boto3):
        first = {"Items": [{"app": "message", "id": "p1"}], "LastEvaluatedKey": {"id": "p1"}}
        second = {"Items": [{"app": "message", "id": "p2"}]}
        mock_boto3["table"].query.side_effect = [first, second]
        result = DynamoClient().query(
            "vimal",
            key_condition_expression="app = :app",
            expression_attr_values={":app": "message"},
        )
        assert result == [{"app": "message", "id": "p1"}, {"app": "message", "id": "p2"}]


class TestScan:
    def test_scan(self, mock_boto3):
        result = DynamoClient().scan("vimal")
        assert len(result) == 2

    def test_scan_pagination(self, mock_boto3):
        first = {"Items": [{"app": "message", "id": "a"}], "LastEvaluatedKey": {"id": "a"}}
        second = {"Items": [{"app": "message", "id": "b"}]}
        mock_boto3["table"].scan.side_effect = [first, second]
        result = DynamoClient().scan("vimal")
        assert result == [{"app": "message", "id": "a"}, {"app": "message", "id": "b"}]


class TestListTables:
    def test_list(self, mock_boto3):
        assert DynamoClient().list_tables() == ["vimal"]
