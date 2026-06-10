from pydantic import BaseModel


class ItemResponse(BaseModel):
    item: dict | None = None


class ItemListResponse(BaseModel):
    items: list[dict]
    count: int


class QueryRequest(BaseModel):
    key_condition_expression: str
    expression_attr_values: dict
    expression_attr_names: dict | None = None
    filter_expression: str | None = None
    index_name: str | None = None
    limit: int | None = None


class ScanRequest(BaseModel):
    filter_expression: str | None = None
    expression_attr_values: dict | None = None
    expression_attr_names: dict | None = None
    limit: int | None = None


class UpdateRequest(BaseModel):
    key: dict
    update_expression: str
    expression_attr_values: dict
    expression_attr_names: dict | None = None


class DeleteResponse(BaseModel):
    deleted: bool


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "clio"
