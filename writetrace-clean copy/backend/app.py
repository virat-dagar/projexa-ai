# app.py
from statistics import median
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Allow frontend to call backend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Submission(BaseModel):
    text: str
    total_chars: int
    total_words: int
    startTime: int
    endTime: int
    duration_seconds: int
    events: List[Dict[str, Any]]


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_event_type(event: Dict[str, Any]) -> str:
    value = event.get("type", "")
    return value if isinstance(value, str) else ""


def extract_features(sub: Submission) -> Dict[str, Any]:
    events = sub.events or []

    key_events = [event for event in events if safe_event_type(event) == "key"]
    paste_events = [event for event in events if safe_event_type(event) == "paste"]
    edit_events = [event for event in events if safe_event_type(event) == "edit"]
    large_inserts = [event for event in events if safe_event_type(event) == "large_insert"]
    sudden_inserts = [event for event in events if safe_event_type(event) == "sudden_insert"]

    total_chars = max(sub.total_chars, len(sub.text or ""), 0)
    total_words = max(sub.total_words, len((sub.text or "").split()), 0)
    total_time = max(sub.duration_seconds, 0)
    total_time_minutes = total_time / 60 if total_time else 0

    gaps = [
        safe_int(event.get("gap"))
        for event in key_events
        if event.get("gap") is not None
    ]

    total_pasted_chars = sum(max(safe_int(event.get("length")), 0) for event in paste_events)
    paste_lengths = [max(safe_int(event.get("length")), 0) for event in paste_events]
    sudden_insert_lengths = [max(safe_int(event.get("length")), 0) for event in sudden_inserts]
    large_insert_lengths = [max(safe_int(event.get("length")), 0) for event in large_inserts]

    paste_ratio = total_pasted_chars / max(total_chars, 1)
    typed_chars_estimate = max(total_chars - total_pasted_chars, 0)
    typed_ratio = typed_chars_estimate / max(total_chars, 1)

    active_typing_seconds = sum(min(gap, 10000) for gap in gaps if gap > 0) / 1000
    active_typing_seconds = min(active_typing_seconds, total_time)

    words_per_minute = total_words / total_time_minutes if total_time_minutes else 0
    chars_per_minute = total_chars / total_time_minutes if total_time_minutes else 0

    return {
        "total_events": len(events),
        "key_event_count": len(key_events),
        "paste_event_count": len(paste_events),
        "edit_event_count": len(edit_events),
        "large_insert_count": len(large_inserts),
        "sudden_insert_count": len(sudden_inserts),
        "total_time_seconds": total_time,
        "total_words": total_words,
        "total_chars": total_chars,
        "avg_key_gap_ms": round(sum(gaps) / len(gaps), 2) if gaps else 0,
        "median_key_gap_ms": round(median(gaps), 2) if gaps else 0,
        "long_pause_count": sum(1 for gap in gaps if gap > 300000),
        "pause_count_over_30s": sum(1 for gap in gaps if gap > 30000),
        "total_pasted_chars": total_pasted_chars,
        "paste_ratio": round(paste_ratio, 4),
        "max_paste_chars": max(paste_lengths, default=0),
        "average_paste_chars": round(sum(paste_lengths) / len(paste_lengths), 2) if paste_lengths else 0,
        "typed_chars_estimate": typed_chars_estimate,
        "typed_ratio": round(typed_ratio, 4),
        "max_large_insert_chars": max(large_insert_lengths, default=0),
        "max_sudden_insert_chars": max(sudden_insert_lengths, default=0),
        "active_typing_seconds_estimate": round(active_typing_seconds, 2),
        "words_per_minute": round(words_per_minute, 2),
        "chars_per_minute": round(chars_per_minute, 2),
    }


def build_metric_summary(features: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "time_spent_minutes": round(features["total_time_seconds"] / 60, 2),
        "words": features["total_words"],
        "characters": features["total_chars"],
        "words_per_minute": features["words_per_minute"],
        "paste_ratio_percent": round(features["paste_ratio"] * 100, 1),
        "typed_ratio_percent": round(features["typed_ratio"] * 100, 1),
        "paste_events": features["paste_event_count"],
        "largest_paste_chars": features["max_paste_chars"],
        "sudden_inserts": features["sudden_insert_count"],
        "largest_sudden_insert_chars": features["max_sudden_insert_chars"],
        "long_pauses": features["long_pause_count"],
        "key_events": features["key_event_count"],
    }


def add_signal(
    signals: List[Dict[str, Any]],
    *,
    direction: str,
    weight: int,
    label: str,
    detail: str,
) -> None:
    signals.append(
        {
            "direction": direction,
            "weight": weight,
            "label": label,
            "detail": detail,
        }
    )


def classify_risk(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 40:
        return "moderate"
    return "low"


def build_summary(score: int, level: str, signals: List[Dict[str, Any]]) -> str:
    strongest = [signal["label"] for signal in signals if signal["direction"] == "risk"][:2]
    reassuring = [signal["label"] for signal in signals if signal["direction"] == "reassuring"][:1]

    if level == "high" and strongest:
        joined = ", ".join(strongest)
        return f"High-risk submission pattern detected, mainly due to {joined.lower()}."

    if level == "moderate" and strongest:
        joined = ", ".join(strongest)
        return f"Moderate-risk submission pattern. The main concerns are {joined.lower()}."

    if reassuring:
        return f"Low-risk submission pattern with reassuring signs such as {reassuring[0].lower()}."

    return "Low-risk submission pattern with limited suspicious indicators."


def score_submission(features: Dict[str, Any]) -> Dict[str, Any]:
    risk_score = 0
    signals: List[Dict[str, Any]] = []

    if features["paste_ratio"] >= 0.6:
        risk_score += 32
        add_signal(
            signals,
            direction="risk",
            weight=32,
            label="Very high pasted content",
            detail=f"{round(features['paste_ratio'] * 100, 1)}% of the final text appears to come from paste events.",
        )
    elif features["paste_ratio"] >= 0.35:
        risk_score += 20
        add_signal(
            signals,
            direction="risk",
            weight=20,
            label="Heavy pasted content",
            detail=f"{round(features['paste_ratio'] * 100, 1)}% of the final text appears to come from paste events.",
        )
    elif features["paste_ratio"] <= 0.1 and features["typed_ratio"] >= 0.85:
        risk_score -= 8
        add_signal(
            signals,
            direction="reassuring",
            weight=8,
            label="Mostly typed drafting",
            detail="Most of the final text appears to have been typed inside the editor.",
        )

    if features["max_paste_chars"] >= 1200:
        risk_score += 28
        add_signal(
            signals,
            direction="risk",
            weight=28,
            label="Massive single paste block",
            detail=f"A single paste added {features['max_paste_chars']} characters.",
        )
    elif features["max_paste_chars"] >= 400:
        risk_score += 14
        add_signal(
            signals,
            direction="risk",
            weight=14,
            label="Large paste block",
            detail=f"A single paste added {features['max_paste_chars']} characters.",
        )

    if features["sudden_insert_count"] >= 2:
        risk_score += 20
        add_signal(
            signals,
            direction="risk",
            weight=20,
            label="Repeated sudden insertions",
            detail=f"{features['sudden_insert_count']} large instant insertions were detected.",
        )
    elif features["sudden_insert_count"] == 1:
        risk_score += 10
        add_signal(
            signals,
            direction="risk",
            weight=10,
            label="Sudden insertion detected",
            detail=f"One instant insertion of up to {features['max_sudden_insert_chars']} characters was detected.",
        )

    if features["total_words"] >= 200 and features["key_event_count"] <= 5:
        risk_score += 30
        add_signal(
            signals,
            direction="risk",
            weight=30,
            label="Very low typing evidence",
            detail="The final document is sizable, but only a small number of key events were recorded.",
        )
    elif features["total_words"] >= 200 and features["key_event_count"] >= 80:
        risk_score -= 6
        add_signal(
            signals,
            direction="reassuring",
            weight=6,
            label="Strong typing evidence",
            detail=f"{features['key_event_count']} key events were recorded while building the submission.",
        )

    if features["total_time_seconds"] > 0 and features["total_words"] >= 150:
        if features["words_per_minute"] >= 90:
            risk_score += 18
            add_signal(
                signals,
                direction="risk",
                weight=18,
                label="Implausibly fast writing speed",
                detail=f"The submission rate was {features['words_per_minute']} words per minute.",
            )
        elif features["words_per_minute"] <= 35 and features["typed_ratio"] >= 0.75:
            risk_score -= 5
            add_signal(
                signals,
                direction="reassuring",
                weight=5,
                label="Natural drafting speed",
                detail=f"The submission rate was {features['words_per_minute']} words per minute.",
            )

    if features["total_time_seconds"] <= 300 and features["total_words"] >= 120:
        risk_score += 18
        add_signal(
            signals,
            direction="risk",
            weight=18,
            label="Very short overall writing time",
            detail=f"The full submission was produced in {round(features['total_time_seconds'] / 60, 1)} minutes.",
        )
    elif features["total_time_seconds"] >= 1800 and features["typed_ratio"] >= 0.7:
        risk_score -= 7
        add_signal(
            signals,
            direction="reassuring",
            weight=7,
            label="Sustained writing session",
            detail=f"The session lasted {round(features['total_time_seconds'] / 60, 1)} minutes.",
        )

    if features["long_pause_count"] >= 2 and features["typed_ratio"] >= 0.6:
        risk_score -= 4
        add_signal(
            signals,
            direction="reassuring",
            weight=4,
            label="Revision-style pauses",
            detail="The session includes long pauses that are consistent with drafting and revising.",
        )

    risk_score = round(clamp(risk_score, 0, 100))
    risk_level = classify_risk(risk_score)

    signals.sort(key=lambda signal: signal["weight"], reverse=True)
    top_risk_signals = [signal["label"] for signal in signals if signal["direction"] == "risk"][:4]

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "summary": build_summary(risk_score, risk_level, signals),
        "signals": signals,
        "reasons": top_risk_signals,
    }


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/submit")
def receive_submission(sub: Submission) -> Dict[str, Any]:
    features = extract_features(sub)
    scoring = score_submission(features)
    metrics = build_metric_summary(features)

    response = {
        "risk": scoring["risk_score"],
        "risk_score": scoring["risk_score"],
        "risk_level": scoring["risk_level"],
        "summary": scoring["summary"],
        "reasons": scoring["reasons"],
        "signals": scoring["signals"],
        "metrics": metrics,
        "features": features,
    }

    print("\n--- New Submission ---")
    print("Words:", sub.total_words)
    print("Duration:", sub.duration_seconds, "seconds")
    print("Metrics:", metrics)
    print("Risk:", response["risk_score"], response["risk_level"])
    print("Summary:", response["summary"])
    print("Reasons:", response["reasons"])
    print("----------------------\n")

    return response
