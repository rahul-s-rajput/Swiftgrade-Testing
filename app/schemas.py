from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any


class SessionCreateRes(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    session_id: str
    status: str = "created"


class SessionListItem(BaseModel):
    id: str
    status: str
    created_at: str
    name: Optional[str] = None
    selected_models: Optional[List[str]] = None
    default_tries: Optional[int] = None
    rubric_models: Optional[List[str]] = None      # Legacy: Rubric model names
    assessment_models: Optional[List[str]] = None  # Legacy: Assessment model names
    model_pairs: Optional[List[Dict[str, Any]]] = None  # NEW: Complete model pair specifications with reasoning


class ImageRegisterReq(BaseModel):
    session_id: str
    role: str = Field(..., pattern=r"^(student|answer_key|grading_rubric)$")
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


class QuestionConfigQuestionSimple(BaseModel):
    """Simplified question config that doesn't require number field"""
    question_id: str
    max_marks: float = Field(..., ge=0)


class QuestionConfigReq(BaseModel):
    session_id: str
    questions: List[Dict[str, Any]]  # Accept both formats as dicts
    human_marks_by_qid: Dict[str, float]


class OkRes(BaseModel):
    ok: bool = True


# --- Story 22: Async Grading via OpenRouter ---

class GradeModelSpec(BaseModel):
    name: str
    tries: Optional[int] = None
    reasoning: Optional[Dict[str, Any]] = None  # Per-model reasoning config
    instance_id: Optional[str] = None  # Optional identifier for same model with different reasoning


# --- Grading Rubric: Model Pairs ---

class ModelPairSpec(BaseModel):
    """Specification for a rubric model + assessment model pair"""
    rubric_model: GradeModelSpec
    assessment_model: GradeModelSpec
    instance_id: Optional[str] = None  # Unique identifier for this pair


class GradeSingleReq(BaseModel):
    session_id: str
    # New: Model pairs for rubric-based grading
    model_pairs: Optional[List[ModelPairSpec]] = None
    # Legacy: Single models (kept for backward compatibility)
    models: Optional[List[GradeModelSpec]] = None
    default_tries: Optional[int] = 1
    reasoning: Optional[Dict[str, Any]] = None  # pass-through to OpenRouter for models that support it


class GradeSingleRes(BaseModel):
    ok: bool = True
    session_id: str


# --- Session Config API ---
class SessionCreateReq(BaseModel):
    name: Optional[str] = None

class SessionConfigReq(BaseModel):
    selected_models: List[str]
    default_tries: int = 1


# --- Story 23: Results API ---

class TokenUsageItem(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: Optional[int] = None
    total_tokens: int = 0
    cost_estimate: Optional[float] = None


class ResultItem(BaseModel):
    try_index: int
    marks_awarded: Optional[float] = None
    rubric_notes: Optional[str] = None
    token_usage: Optional[TokenUsageItem] = None


class ResultsRes(BaseModel):
    session_id: str
    results_by_question: Dict[str, Dict[str, List[ResultItem]]]


# --- Story 24: Stats & Discrepancies API ---
class StatsRes(BaseModel):
    session_id: str
    human_marks_by_qid: Dict[str, float]
    totals: Dict[str, Any]
    discrepancies_by_model_try: Dict[str, Any]


# --- Results Errors API (for UI failure reasons) ---
class ResultsErrorsRes(BaseModel):
    session_id: str
    # errors_by_model_try[model][try_index] -> list of validation error dicts
    errors_by_model_try: Dict[str, Dict[str, List[Dict[str, Any]]]]


# --- Questions GET API ---
class QuestionsRes(BaseModel):
    session_id: str
    questions: List[QuestionConfigQuestion]


# --- Prompt Settings API ---
class PromptSettingsRes(BaseModel):
    system_template: str
    user_template: str
    schema_template: str  # JSON response schema template


class PromptSettingsReq(BaseModel):
    system_template: str
    user_template: str
    schema_template: str  # JSON response schema template


# --- Rubric Prompt Settings API ---
class RubricPromptSettingsRes(BaseModel):
    """Response schema for grading rubric prompt templates"""
    system_template: str
    user_template: str


class RubricPromptSettingsReq(BaseModel):
    """Request schema for updating grading rubric prompt templates"""
    system_template: str
    user_template: str


# --- Rubric Results API ---
class RubricResultItem(BaseModel):
    """Single rubric result for a specific try"""
    try_index: int
    rubric_response: str | None = None
    validation_errors: Dict[str, Any] | None = None


class RubricResultsRes(BaseModel):
    """Response schema for rubric results"""
    session_id: str
    # rubric_results[model_name][try_index] = RubricResultItem
    rubric_results: Dict[str, Dict[str, RubricResultItem]]
