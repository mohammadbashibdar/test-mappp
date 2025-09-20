from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, Field
# from pydantic.generics import GenericModel
from typing import Generic

T = TypeVar("T")

class Meta(BaseModel):
    offset: Optional[int]
    limit: Optional[int]
    total: Optional[int]

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: Union[T, List[T], None] = None
    meta: Optional[Meta] = None
    model_config = {
        "from_attributes": True  # معادل orm_mode=True در نسخه جدید
    }

class ErrorResponse(BaseModel, Generic[T]):
    success: bool = False
    message: str
    code: int
    data: Union[T, List[T], None] = None
    errors: Optional[Dict[str, str]] = None
