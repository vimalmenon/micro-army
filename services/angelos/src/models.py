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
