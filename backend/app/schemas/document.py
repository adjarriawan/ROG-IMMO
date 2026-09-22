from pydantic import BaseModel


class DocumentCreateRequest(BaseModel):
    filename: str
    content: str


class DocumentResponse(BaseModel):
    filename: str
    status: str
