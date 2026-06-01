from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Submission(BaseModel):
    text: str
    total_chars: int
    total_words: int
    startTime: int
    endTime: int
    duration_seconds: int
    events: List[Dict[str, Any]]


class StudentSubmissionRequest(Submission):
    student_name: str
    student_id: str


class AssignmentCreateRequest(BaseModel):
    title: str
    description: str
    due_date: str
    max_score: int = Field(default=100, ge=1)
