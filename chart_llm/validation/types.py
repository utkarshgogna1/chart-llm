"""Shared types for the validation layer."""

from typing import Literal, Optional

from pydantic import BaseModel

ValidationStage = Literal["schema", "columns", "semantics", "data_ref"]


class ValidationError(BaseModel):
    stage: ValidationStage
    code: str
    message: str
    path: str
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    ok: bool
    errors: list[ValidationError]
    stage_failed: Optional[ValidationStage] = None
