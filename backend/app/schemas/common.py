from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Meta(BaseModel):
    page: int = 1
    page_size: int = 25
    total: int = 0


class Envelope(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    data: T


class ListEnvelope(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    data: list[T]
    meta: Meta


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict = {}
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody
