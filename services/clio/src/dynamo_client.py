import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from config import settings

logger = logging.getLogger(__name__)


class DynamoClient:
    _instance: "DynamoClient | None" = None

    def __new__(cls) -> "DynamoClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self) -> None:
        kwargs = {
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
            "region_name": settings.aws_region,
        }
        if settings.dynamo_endpoint_url:
            kwargs["endpoint_url"] = settings.dynamo_endpoint_url

        self._resource = boto3.resource("dynamodb", **kwargs)
        logger.info("DynamoDB client initialized (region=%s)", settings.aws_region)

    def _table(self, table_name: str):
        return self._resource.Table(table_name)

    def get_item(self, table_name: str, key: dict[str, Any]) -> dict[str, Any] | None:
        try:
            resp = self._table(table_name).get_item(Key=key)
            return resp.get("Item")
        except (ClientError, BotoCoreError) as e:
            logger.error("get_item failed: %s", e)
            raise

    def put_item(self, table_name: str, item: dict[str, Any]) -> dict[str, Any]:
        try:
            self._table(table_name).put_item(Item=item)
            return item
        except (ClientError, BotoCoreError) as e:
            logger.error("put_item failed: %s", e)
            raise

    def update_item(
        self,
        table_name: str,
        key: dict[str, Any],
        update_expression: str,
        expression_attr_values: dict[str, Any],
        expression_attr_names: dict[str, str] | None = None,
        return_values: str = "ALL_NEW",
    ) -> dict[str, Any] | None:
        try:
            kwargs = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_attr_values,
                "ReturnValues": return_values,
            }
            if expression_attr_names:
                kwargs["ExpressionAttributeNames"] = expression_attr_names
            resp = self._table(table_name).update_item(**kwargs)
            return resp.get("Attributes")
        except (ClientError, BotoCoreError) as e:
            logger.error("update_item failed: %s", e)
            raise

    def delete_item(self, table_name: str, key: dict[str, Any]) -> bool:
        try:
            self._table(table_name).delete_item(Key=key)
            return True
        except (ClientError, BotoCoreError) as e:
            logger.error("delete_item failed: %s", e)
            raise

    def query(
        self,
        table_name: str,
        key_condition_expression: str,
        expression_attr_values: dict[str, Any],
        expression_attr_names: dict[str, str] | None = None,
        filter_expression: str | None = None,
        index_name: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        try:
            kwargs = {
                "KeyConditionExpression": key_condition_expression,
                "ExpressionAttributeValues": expression_attr_values,
            }
            if expression_attr_names:
                kwargs["ExpressionAttributeNames"] = expression_attr_names
            if filter_expression:
                kwargs["FilterExpression"] = filter_expression
            if index_name:
                kwargs["IndexName"] = index_name
            if limit:
                kwargs["Limit"] = limit

            items: list[dict[str, Any]] = []
            resp = self._table(table_name).query(**kwargs)
            items.extend(resp.get("Items", []))

            while "LastEvaluatedKey" in resp:
                kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
                if limit:
                    kwargs["Limit"] = limit - len(items)
                    if kwargs["Limit"] <= 0:
                        break
                resp = self._table(table_name).query(**kwargs)
                items.extend(resp.get("Items", []))

            return items
        except (ClientError, BotoCoreError) as e:
            logger.error("query failed: %s", e)
            raise

    def scan(
        self,
        table_name: str,
        filter_expression: str | None = None,
        expression_attr_values: dict[str, Any] | None = None,
        expression_attr_names: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        try:
            kwargs: dict[str, Any] = {}
            if filter_expression:
                kwargs["FilterExpression"] = filter_expression
            if expression_attr_values:
                kwargs["ExpressionAttributeValues"] = expression_attr_values
            if expression_attr_names:
                kwargs["ExpressionAttributeNames"] = expression_attr_names
            if limit:
                kwargs["Limit"] = limit

            items: list[dict[str, Any]] = []
            resp = self._table(table_name).scan(**kwargs)
            items.extend(resp.get("Items", []))

            while "LastEvaluatedKey" in resp:
                kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
                if limit:
                    kwargs["Limit"] = limit - len(items)
                    if kwargs["Limit"] <= 0:
                        break
                resp = self._table(table_name).scan(**kwargs)
                items.extend(resp.get("Items", []))

            return items
        except (ClientError, BotoCoreError) as e:
            logger.error("scan failed: %s", e)
            raise

