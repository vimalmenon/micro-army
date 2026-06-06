from pydantic import BaseModel, EmailStr


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "messages-svc"


class CreateMessageRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str


class UpdateMessageRequest(BaseModel):
    read: bool | None = None
    subject: str | None = None


class MessageResponse(BaseModel):
    message: dict


class MessageListResponse(BaseModel):
    messages: list[dict]
    count: int


class DeleteResponse(BaseModel):
    deleted: bool
