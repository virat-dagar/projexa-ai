from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from .analysis import analyze_submission, extract_flagged_sections, extract_paste_sections
from .models import AssignmentCreateRequest, StudentSubmissionRequest, Submission
from .storage import JsonWriteTraceStore, make_id, now_iso


def log_analysis(submission: Submission, response: Dict[str, Any]) -> None:
    print("\n--- New Submission ---")
    print("Words:", submission.total_words)
    print("Duration:", submission.duration_seconds, "seconds")
    print("Metrics:", response["metrics"])
    print(
        "Behavior risk:",
        response["behavior_analysis"]["risk_score"],
        response["behavior_analysis"]["risk_level"],
    )
    print(
        "Content risk:",
        response["content_analysis"]["risk_score"],
        response["content_analysis"]["risk_level"],
    )
    print("Combined risk:", response["risk_score"], response["risk_level"])
    print("Summary:", response["summary"])
    print("Reasons:", response["reasons"])
    print("----------------------\n")


def create_router(store: JsonWriteTraceStore) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health_check() -> Dict[str, str]:
        return {"status": "ok", "storage": str(store.data_file)}

    @router.post("/submit")
    def receive_submission(submission: Submission) -> Dict[str, Any]:
        response = analyze_submission(submission)
        log_analysis(submission, response)
        return response

    @router.get("/assignments/public")
    def get_public_assignments() -> Dict[str, Any]:
        return {"assignments": store.list_public_assignments()}

    @router.post("/teacher/assignments")
    def create_assignment(payload: AssignmentCreateRequest) -> Dict[str, Any]:
        title = payload.title.strip()
        description = payload.description.strip()
        due_date = payload.due_date.strip()

        if not title:
            raise HTTPException(status_code=400, detail="Assignment title is required.")

        if not description:
            raise HTTPException(status_code=400, detail="Assignment description is required.")

        if not due_date:
            raise HTTPException(status_code=400, detail="Assignment due date is required.")

        return store.create_assignment(
            title=title,
            description=description,
            due_date=due_date,
            max_score=payload.max_score,
        )

    @router.get("/teacher/assignments")
    def get_teacher_assignments() -> Dict[str, Any]:
        return {"assignments": store.list_teacher_assignments()}

    @router.post("/assignments/{assignment_id}/submit")
    def submit_assignment(assignment_id: str, payload: StudentSubmissionRequest) -> Dict[str, Any]:
        assignment = store.get_assignment(assignment_id)
        if assignment is None:
            raise HTTPException(status_code=404, detail="Assignment not found.")

        submission = Submission(
            text=payload.text,
            total_chars=payload.total_chars,
            total_words=payload.total_words,
            startTime=payload.startTime,
            endTime=payload.endTime,
            duration_seconds=payload.duration_seconds,
            events=payload.events,
        )
        analysis = analyze_submission(submission)
        paste_sections = extract_paste_sections(payload.events)
        flagged_sections = extract_flagged_sections(payload.text)
        submission_id = make_id("sub")

        submission_record = {
            "id": submission_id,
            "assignment_id": assignment_id,
            "assignment_title": assignment["title"],
            "student_name": payload.student_name.strip() or "Unknown Student",
            "student_id": payload.student_id.strip() or "unknown",
            "submitted_at": now_iso(),
            "analysis": analysis,
            "paste_sections": paste_sections,
            "flagged_sections": flagged_sections,
        }

        try:
            store.add_submission(assignment_id, submission_record)
        except KeyError:
            raise HTTPException(status_code=404, detail="Assignment not found.") from None

        return {
            "status": "submitted",
            "message": "Submission received and sent to teacher dashboard for review.",
            "submission_id": submission_id,
            "assignment_id": assignment_id,
        }

    @router.get("/teacher/assignments/{assignment_id}/submissions")
    def get_assignment_submissions(assignment_id: str) -> Dict[str, Any]:
        assignment, submissions = store.get_assignment_submission_summaries(assignment_id)
        if assignment is None:
            raise HTTPException(status_code=404, detail="Assignment not found.")

        return {"assignment": assignment, "submissions": submissions}

    @router.get("/teacher/submissions/{submission_id}")
    def get_submission_detail(submission_id: str) -> Dict[str, Any]:
        submission = store.get_submission(submission_id)
        if submission is None:
            raise HTTPException(status_code=404, detail="Submission not found.")

        return submission

    return router
