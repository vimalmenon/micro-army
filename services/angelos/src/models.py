from pydantic import BaseModel, EmailStr


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "angelos"


class CreateMessageRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str


class MessageResponse(BaseModel):
    id: str
    status: str = "submitted"


class MessageDetail(BaseModel):
    id: str
    app: str
    name: str
    email: str
    subject: str
    message: str
    read: bool
    created_at: str
    updated_at: str


class MessageListResponse(BaseModel):
    messages: list[MessageDetail]
    count: int


class MessageUpdateResponse(BaseModel):
    id: str
    read: bool
    status: str = "updated"


class MessageDeleteResponse(BaseModel):
    id: str
    deleted: bool = True
    status: str = "deleted"
