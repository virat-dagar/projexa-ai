import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class JsonWriteTraceStore:
    def __init__(self, data_file: Path) -> None:
        self.data_file = data_file
        self._lock = RLock()
        self._state = self._empty_state()

    @staticmethod
    def _empty_state() -> Dict[str, Dict[str, Any]]:
        return {"assignments": {}, "submissions": {}}

    def _load_unlocked(self) -> None:
        try:
            raw_state = json.loads(self.data_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw_state = self._empty_state()
        except json.JSONDecodeError:
            raw_state = self._empty_state()

        assignments = raw_state.get("assignments", {})
        submissions = raw_state.get("submissions", {})
        self._state = {
            "assignments": assignments if isinstance(assignments, dict) else {},
            "submissions": submissions if isinstance(submissions, dict) else {},
        }

    def _persist_unlocked(self) -> None:
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.data_file.parent,
            prefix=f".{self.data_file.name}.",
            delete=False,
        ) as temp_file:
            json.dump(self._state, temp_file, indent=2, sort_keys=True)
            temp_name = temp_file.name

        os.replace(temp_name, self.data_file)

    def _copy(self, value: Any) -> Any:
        return copy.deepcopy(value)

    def list_public_assignments(self) -> List[Dict[str, Any]]:
        with self._lock:
            self._load_unlocked()
            assignment_list = sorted(
                self._state["assignments"].values(),
                key=lambda item: item["created_at"],
                reverse=True,
            )

            return [
                {
                    "id": assignment["id"],
                    "title": assignment["title"],
                    "description": assignment["description"],
                    "due_date": assignment["due_date"],
                    "max_score": assignment["max_score"],
                    "created_at": assignment["created_at"],
                    "submission_count": len(assignment["submission_ids"]),
                }
                for assignment in assignment_list
            ]

    def create_assignment(
        self,
        *,
        title: str,
        description: str,
        due_date: str,
        max_score: int,
    ) -> Dict[str, Any]:
        with self._lock:
            self._load_unlocked()
            assignment_id = make_id("asg")
            assignment = {
                "id": assignment_id,
                "title": title,
                "description": description,
                "due_date": due_date,
                "max_score": max(max_score, 1),
                "created_at": now_iso(),
                "submission_ids": [],
            }
            self._state["assignments"][assignment_id] = assignment
            self._persist_unlocked()
            return self._copy(assignment)

    def list_teacher_assignments(self) -> List[Dict[str, Any]]:
        with self._lock:
            self._load_unlocked()
            assignment_rows: List[Dict[str, Any]] = []
            assignments = sorted(
                self._state["assignments"].values(),
                key=lambda item: item["created_at"],
                reverse=True,
            )

            for assignment in assignments:
                scores = [
                    self._state["submissions"][submission_id]["analysis"]["risk_score"]
                    for submission_id in assignment["submission_ids"]
                    if submission_id in self._state["submissions"]
                ]
                assignment_rows.append(
                    {
                        **assignment,
                        "submission_count": len(assignment["submission_ids"]),
                        "average_risk_score": round(sum(scores) / len(scores), 1) if scores else None,
                    }
                )

            return self._copy(assignment_rows)

    def get_assignment(self, assignment_id: str) -> Dict[str, Any] | None:
        with self._lock:
            self._load_unlocked()
            assignment = self._state["assignments"].get(assignment_id)
            return self._copy(assignment) if assignment else None

    def add_submission(self, assignment_id: str, submission_record: Dict[str, Any]) -> None:
        with self._lock:
            self._load_unlocked()
            assignment = self._state["assignments"].get(assignment_id)
            if assignment is None:
                raise KeyError(assignment_id)

            self._state["submissions"][submission_record["id"]] = submission_record
            assignment["submission_ids"].append(submission_record["id"])
            self._persist_unlocked()

    def get_assignment_submission_summaries(
        self,
        assignment_id: str,
    ) -> tuple[Dict[str, Any] | None, List[Dict[str, Any]]]:
        with self._lock:
            self._load_unlocked()
            assignment = self._state["assignments"].get(assignment_id)
            if assignment is None:
                return None, []

            submissions = [
                {
                    "id": submission["id"],
                    "student_name": submission["student_name"],
                    "student_id": submission["student_id"],
                    "submitted_at": submission["submitted_at"],
                    "risk_score": submission["analysis"]["risk_score"],
                    "risk_level": submission["analysis"]["risk_level"],
                    "summary": submission["analysis"]["summary"],
                    "paste_section_count": len(submission["paste_sections"]),
                    "flagged_section_count": len(submission["flagged_sections"]),
                }
                for submission_id in assignment["submission_ids"]
                for submission in [self._state["submissions"].get(submission_id)]
                if submission is not None
            ]

            submissions.sort(key=lambda item: item["submitted_at"], reverse=True)
            return self._copy(assignment), self._copy(submissions)

    def get_submission(self, submission_id: str) -> Dict[str, Any] | None:
        with self._lock:
            self._load_unlocked()
            submission = self._state["submissions"].get(submission_id)
            return self._copy(submission) if submission else None
