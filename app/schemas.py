from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List


class SessionCreateRes(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    session_id: str
    status: str = "created"


class ImageRegisterReq(BaseModel):
    session_id: str
    role: str = Field(..., pattern=r"^(student|answer_key)$")
    url: str
    order_index: int = Field(..., ge=0)


class SignedUrlReq(BaseModel):
    filename: str
    content_type: str = Field(..., description="MIME type, e.g. image/png")


class SignedUrlRes(BaseModel):
    uploadUrl: str
    token: Optional[str] = None
    path: str
    headers: Dict[str, str]
    publicUrl: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
    correlation_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- Story 21: Question Config + Human Marks ---

class QuestionConfigQuestion(BaseModel):
    question_id: str
    number: int = Field(..., ge=1)
    max_marks: float = Field(..., ge=0)


class QuestionConfigReq(BaseModel):
    session_id: str
    questions: List[QuestionConfigQuestion]
    human_marks_by_qid: Dict[str, float]


class OkRes(BaseModel):
    ok: bool = True
