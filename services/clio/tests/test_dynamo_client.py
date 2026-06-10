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
    """Mock boto3.resource and all DynamoDB table methods."""
    with patch("dynamo_client.boto3") as mock_boto3:
        # Mock table methods
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {"app": "message", "id": "abc", "data": "hello"}}
        mock_table.put_item.return_value = {}
        mock_table.update_item.return_value = {"Attributes": {"app": "message", "data": "updated"}}
        mock_table.delete_item.return_value = {}
        mock_table.query.return_value = {"Items": [{"app": "q1"}, {"app": "q2"}]}
        mock_table.scan.return_value = {"Items": [{"app": "s1"}, {"app": "s2"}]}

        # Mock resource
        mock_resource = MagicMock()
        mock_resource.Table.return_value = mock_table
        class MockTable:
            name = "vimal"
        mock_resource.tables.all.return_value = [MockTable()]

        mock_boto3.resource.return_value = mock_resource

        yield {
            "boto3": mock_boto3,
            "resource": mock_resource,
            "table": mock_table,
        }


class TestDynamoClientSingleton:
    def test_singleton_returns_same_instance(self):
        a = DynamoClient()
        b = DynamoClient()
        assert a is b

    def test_singleton_recreated_after_reset(self):
        a = DynamoClient()
        DynamoClient._instance = None
        b = DynamoClient()
        assert a is not b


class TestDynamoClientInit:
    def test_init_calls_boto3_with_settings(self, mock_boto3, mock_settings):
        with patch("dynamo_client.settings", mock_settings):
            DynamoClient()
            mock_boto3["boto3"].resource.assert_called_once_with(
                "dynamodb",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
                region_name="us-east-1",
                endpoint_url="http://localhost:8000",
            )

    def test_init_without_endpoint(self, mock_boto3):
        s = MagicMock()
        s.aws_access_key_id = "k"
        s.aws_secret_access_key = "s"
        s.aws_region = "us-east-1"
        s.dynamo_endpoint_url = None

        with patch("dynamo_client.settings", s):
            DynamoClient()
            mock_boto3["boto3"].resource.assert_called_once_with(
                "dynamodb",
                aws_access_key_id="k",
                aws_secret_access_key="s",
                region_name="us-east-1",
            )


class TestDynamoClientMethods:
    def test_get_item_found(self, mock_boto3):
        client = DynamoClient()
        result = client.get_item("vimal", {"app": "message", "id": "abc"})
        assert result == {"app": "message", "id": "abc", "data": "hello"}
        mock_boto3["table"].get_item.assert_called_once_with(Key={"app": "message", "id": "abc"})

    def test_get_item_not_found(self, mock_boto3):
        mock_boto3["table"].get_item.return_value = {}
        client = DynamoClient()
        result = client.get_item("vimal", {"app": "missing"})
        assert result is None

    def test_get_item_raises_on_error(self, mock_boto3):
        mock_boto3["table"].get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalServerError"}}, "GetItem"
        )
        client = DynamoClient()
        with pytest.raises(botocore.exceptions.ClientError):
            client.get_item("vimal", {"app": "abc"})

    def test_put_item(self, mock_boto3):
        client = DynamoClient()
        item = {"app": "message", "id": "abc", "name": "test"}
        result = client.put_item("vimal", item)
        assert result == item
        mock_boto3["table"].put_item.assert_called_once_with(Item=item)

    def test_update_item(self, mock_boto3):
        client = DynamoClient()
        result = client.update_item(
            "vimal",
            key={"app": "message", "id": "abc"},
            update_expression="SET #n = :v",
            expression_attr_values={":v": "updated"},
            expression_attr_names={"#n": "name"},
        )
        assert result == {"app": "message", "data": "updated"}
        mock_boto3["table"].update_item.assert_called_once_with(
            Key={"app": "message", "id": "abc"},
            UpdateExpression="SET #n = :v",
            ExpressionAttributeValues={":v": "updated"},
            ExpressionAttributeNames={"#n": "name"},
            ReturnValues="ALL_NEW",
        )

    def test_update_item_without_attr_names(self, mock_boto3):
        client = DynamoClient()
        client.update_item(
            "vimal",
            key={"app": "message", "id": "abc"},
            update_expression="SET data = :v",
            expression_attr_values={":v": "val"},
        )
        mock_boto3["table"].update_item.assert_called_once_with(
            Key={"app": "message", "id": "abc"},
            UpdateExpression="SET data = :v",
            ExpressionAttributeValues={":v": "val"},
            ReturnValues="ALL_NEW",
        )
        # ExpressionAttributeNames should NOT be in the call kwargs
        call_kwargs = mock_boto3["table"].update_item.call_args.kwargs
        assert "ExpressionAttributeNames" not in call_kwargs

    def test_delete_item(self, mock_boto3):
        client = DynamoClient()
        result = client.delete_item("vimal", {"app": "message", "id": "abc"})
        assert result is True
        mock_boto3["table"].delete_item.assert_called_once_with(Key={"app": "message", "id": "abc"})

    def test_query(self, mock_boto3):
        client = DynamoClient()
        result = client.query(
            "vimal",
            key_condition_expression="app = :app",
            expression_attr_values={":app": "message"},
            index_name="gsi1",
            limit=5,
        )
        assert len(result) == 2
        mock_boto3["table"].query.assert_called_once_with(
            KeyConditionExpression="app = :app",
            ExpressionAttributeValues={":app": "message"},
            IndexName="gsi1",
            Limit=5,
        )

    def test_scan(self, mock_boto3):
        client = DynamoClient()
        result = client.scan(
            "vimal",
            filter_expression="app = :app",
            expression_attr_values={":app": "message"},
            limit=100,
        )
        assert len(result) == 2
        mock_boto3["table"].scan.assert_called_once_with(
            FilterExpression="app = :app",
            ExpressionAttributeValues={":app": "message"},
            Limit=100,
        )

    def test_scan_no_filter(self, mock_boto3):
        client = DynamoClient()
        result = client.scan("vimal")
        assert len(result) == 2
        # Called with no arguments — no kwargs should include filter/limit
        mock_boto3["table"].scan.assert_called_once_with()

    def test_list_tables(self, mock_boto3):
        client = DynamoClient()
        result = client.list_tables()
        assert result == ["vimal"]

    def test_query_pagination(self, mock_boto3):
        """Simulate pagination with LastEvaluatedKey."""
        first_call = {"Items": [{"app": "p1"}], "LastEvaluatedKey": {"app": "p1"}}
        second_call = {"Items": [{"app": "p2"}]}

        mock_boto3["table"].query.side_effect = [first_call, second_call]

        client = DynamoClient()
        result = client.query(
            "vimal",
            key_condition_expression="app = :app",
            expression_attr_values={":app": "message"},
        )
        assert result == [{"app": "p1"}, {"app": "p2"}]
        assert mock_boto3["table"].query.call_count == 2

    def test_scan_pagination(self, mock_boto3):
        """Simulate pagination with LastEvaluatedKey."""
        first_call = {"Items": [{"app": "a"}], "LastEvaluatedKey": {"app": "a"}}
        second_call = {"Items": [{"app": "b"}]}

        mock_boto3["table"].scan.side_effect = [first_call, second_call]

        client = DynamoClient()
        result = client.scan("vimal")
        assert result == [{"app": "a"}, {"app": "b"}]
        assert mock_boto3["table"].scan.call_count == 2

    def test_query_pagination_limit_stops_early(self, mock_boto3):
        """Should stop paginating once limit is reached."""
        first_call = {"Items": [{"app": "p1"}], "LastEvaluatedKey": {"app": "p1"}}
        second_call = {"Items": [{"app": "p2"}], "LastEvaluatedKey": {"app": "p2"}}

        mock_boto3["table"].query.side_effect = [first_call, second_call]

        client = DynamoClient()
        result = client.query(
            "vimal",
            key_condition_expression="app = :app",
            expression_attr_values={":app": "message"},
            limit=1,
        )
        assert result == [{"app": "p1"}]
        assert mock_boto3["table"].query.call_count == 1  # Second page not fetched
