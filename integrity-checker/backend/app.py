# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI()

# Allow frontend to call backend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Data Models --------

class Submission(BaseModel):
    text: str
    total_chars: int
    total_words: int
    startTime: int
    endTime: int
    duration_seconds: int
    events: List[Dict]

# -------- Feature Extraction --------

def extract_features(sub: Submission):
    events = sub.events

    key_events = [e for e in events if e["type"] == "key"]
    paste_events = [e for e in events if e["type"] == "paste"]
    sudden_inserts = [e for e in events if e["type"] == "sudden_insert"]

    # Typing gaps
    gaps = [e.get("gap", 0) for e in key_events if e.get("gap") is not None]
    avg_gap = sum(gaps) / len(gaps) if gaps else 0

    long_pauses = len([g for g in gaps if g > 300000])  # >5 min

    # Paste stats
    total_pasted = sum(e.get("length", 0) for e in paste_events)
    paste_ratio = total_pasted / max(sub.total_chars, 1)
    max_paste = max([e.get("length", 0) for e in paste_events], default=0)

    return {
        "avg_gap": avg_gap,
        "long_pauses": long_pauses,
        "paste_ratio": paste_ratio,
        "max_paste": max_paste,
        "total_time": sub.duration_seconds,
        "total_words": sub.total_words,
        "sudden_inserts": len(sudden_inserts),
        "max_sudden_insert": max([e.get("length", 0) for e in sudden_inserts], default=0),
    }

# -------- Risk Scoring --------

def score(features):
    risk = 0
    reasons = []

    if features["paste_ratio"] > 0.4:
        risk += 30
        reasons.append("High paste ratio")

    if features["max_paste"] > 300:
        risk += 25
        reasons.append("Large paste block detected")

    if features["total_time"] < 600:
        risk += 20
        reasons.append("Very short writing time")

    if features["long_pauses"] == 0 and features["paste_ratio"] > 0.3:
        risk += 15
        reasons.append("Continuous writing with heavy pasting")
    
    if features["sudden_inserts"] > 0:
        risk += 25
        reasons.append("Sudden large text insertion detected")

    if features["max_sudden_insert"] > 500:
        risk += 30
        reasons.append("Very large instant content insertion")

    return min(risk, 100), reasons

# -------- API Endpoint --------

@app.post("/submit")
def receive_submission(sub: Submission):
    features = extract_features(sub)
    risk, reasons = score(features)

    print("\n--- New Submission ---")
    print("Words:", sub.total_words)
    print("Duration:", sub.duration_seconds, "seconds")
    print("Features:", features)
    print("Risk:", risk)
    print("Reasons:", reasons)
    print("----------------------\n")

    return {
        "risk": risk,
        "reasons": reasons,
        "features": features
    }