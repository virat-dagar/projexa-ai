# app.py
import re
from collections import Counter
from datetime import datetime, timezone
from statistics import median, pstdev
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
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


class StudentSubmissionRequest(Submission):
    student_name: str
    student_id: str


class AssignmentCreateRequest(BaseModel):
    title: str
    description: str
    due_date: str
    max_score: int = 100


ASSIGNMENTS: Dict[str, Dict[str, Any]] = {}
SUBMISSIONS: Dict[str, Dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


OBVIOUS_AI_STYLE_PHRASES = (
    "it is important to note",
    "it is worth noting",
    "it should be noted",
    "in today's world",
    "in today's society",
    "in the modern world",
    "this essay will discuss",
    "this paper will discuss",
    "this highlights the importance",
    "this underscores the importance",
    "plays a crucial role",
    "plays an important role",
    "significant impact",
    "various aspects",
    "a wide range of",
    "multifaceted",
    "ever-evolving",
    "delve into",
    "in conclusion",
    "in summary",
    "to summarize",
    "overall",
    "furthermore",
    "moreover",
    "additionally",
    "consequently",
    "therefore",
)

STRUCTURED_PHRASES = (
    "on the other hand",
    "it can be argued that",
    "one could argue that",
    "this suggests that",
    "this demonstrates that",
    "this indicates that",
    "a key factor is",
    "one of the main reasons",
    "another important factor",
    "this can be attributed to",
    "this raises the question",
    "it is evident that",
    "it is clear that",
)

FILLER_PHRASES = (
    "in many ways",
    "to a large extent",
    "in some cases",
    "generally speaking",
    "in most cases",
    "to some degree",
    "in a number of ways",
    "at its core",
    "from a broader perspective",
    "in a broader context",
)

TRANSITION_PHRASES = (
    "that being said",
    "with that in mind",
    "in light of this",
    "given this",
    "taking this into account",
    "all things considered",
    "as a result of this",
    "in doing so",
)

AI_STYLE_PHRASES = tuple(
    dict.fromkeys(
        OBVIOUS_AI_STYLE_PHRASES
        + STRUCTURED_PHRASES
        + FILLER_PHRASES
        + TRANSITION_PHRASES
    )
)

ABSTRACT_WORDS = {
    "framework",
    "context",
    "dynamic",
    "approach",
    "perspective",
    "implications",
    "considerations",
    "insights",
    "patterns",
    "factors",
    "elements",
    "outcomes",
    "process",
    "structure",
    "function",
}

GENERIC_ACADEMIC_WORDS = ABSTRACT_WORDS | {
    "important",
    "significant",
    "various",
    "crucial",
    "essential",
    "effective",
    "impact",
    "aspects",
    "role",
    "benefits",
    "challenges",
    "society",
    "individuals",
    "development",
    "enhance",
    "improve",
    "promote",
    "ensure",
    "foster",
    "utilize",
    "valuable",
    "numerous",
    "overall",
    "modern",
    "complex",
}

SUSPICIOUS_PATTERNS = (
    ("suggests that", "factor"),
    ("suggests that", "context"),
    ("demonstrates that", "process"),
    ("indicates that", "outcomes"),
    ("important role", "development"),
    ("plays a role", "process"),
    ("plays a role", "structure"),
    ("key aspect", "system"),
    ("important factor", "context"),
    ("broader perspective", "implications"),
)


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


def tokenize_words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text.lower())


def split_sentences(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def count_phrase_hits(text: str, phrases: tuple[str, ...]) -> Dict[str, int]:
    normalized = re.sub(r"\s+", " ", text.lower())
    return {
        phrase: normalized.count(phrase)
        for phrase in phrases
        if normalized.count(phrase) > 0
    }


def get_repeated_ngram_ratio(words: List[str], size: int = 3) -> float:
    if len(words) < size * 2:
        return 0

    ngrams = [" ".join(words[index : index + size]) for index in range(len(words) - size + 1)]
    counts = Counter(ngrams)
    repeated_instances = sum(count - 1 for count in counts.values() if count > 1)
    return repeated_instances / max(len(ngrams), 1)


def get_sentence_start_repetition(sentences: List[str]) -> float:
    starts = []
    for sentence in sentences:
        words = tokenize_words(sentence)
        if len(words) >= 2:
            starts.append(" ".join(words[:2]))

    if len(starts) < 4:
        return 0

    most_common_count = Counter(starts).most_common(1)[0][1]
    return most_common_count / len(starts)


def get_abstract_cluster_count(words: List[str], window_size: int = 12, threshold: int = 3) -> int:
    if len(words) < window_size:
        return 0

    cluster_count = 0
    for index in range(0, len(words) - window_size + 1, window_size):
        window = words[index : index + window_size]
        if sum(1 for word in window if word in ABSTRACT_WORDS) >= threshold:
            cluster_count += 1

    return cluster_count


def get_suspicious_pattern_hits(sentences: List[str]) -> Dict[str, int]:
    hits: Counter[str] = Counter()

    for sentence in sentences:
        normalized = re.sub(r"\s+", " ", sentence.lower())
        for phrase, abstract_word in SUSPICIOUS_PATTERNS:
            if phrase in normalized and re.search(rf"\b{re.escape(abstract_word)}s?\b", normalized):
                hits[f"{phrase} + {abstract_word}"] += 1

    return dict(hits)


def extract_content_features(text: str) -> Dict[str, Any]:
    words = tokenize_words(text)
    sentences = split_sentences(text)
    sentence_lengths = [len(tokenize_words(sentence)) for sentence in sentences]
    word_count = len(words)
    sentence_count = len(sentences)

    average_sentence_words = sum(sentence_lengths) / sentence_count if sentence_count else 0
    sentence_length_cv = (
        pstdev(sentence_lengths) / average_sentence_words
        if sentence_count >= 2 and average_sentence_words
        else 0
    )
    unique_word_ratio = len(set(words)) / max(word_count, 1)
    phrase_hits = count_phrase_hits(text, AI_STYLE_PHRASES)
    structured_phrase_hits = count_phrase_hits(text, STRUCTURED_PHRASES)
    filler_phrase_hits = count_phrase_hits(text, FILLER_PHRASES)
    transition_phrase_hits = count_phrase_hits(text, TRANSITION_PHRASES)
    phrase_hit_count = sum(phrase_hits.values())
    structured_phrase_count = sum(structured_phrase_hits.values())
    filler_phrase_count = sum(filler_phrase_hits.values())
    transition_phrase_count = sum(transition_phrase_hits.values())
    generic_word_count = sum(1 for word in words if word in GENERIC_ACADEMIC_WORDS)
    generic_word_density = generic_word_count / max(word_count, 1) * 100
    abstract_word_count = sum(1 for word in words if word in ABSTRACT_WORDS)
    abstract_word_density = abstract_word_count / max(word_count, 1) * 100
    abstract_cluster_count = get_abstract_cluster_count(words)
    suspicious_pattern_hits = get_suspicious_pattern_hits(sentences)
    repeated_trigram_ratio = get_repeated_ngram_ratio(words)
    sentence_start_repetition = get_sentence_start_repetition(sentences)
    concrete_marker_count = len(re.findall(r"\b\d+(?:\.\d+)?%?\b|\"[^\"]+\"|'[^']+'|\([A-Za-z]+,\s*\d{4}\)", text))
    first_person_count = sum(1 for word in words if word in {"i", "me", "my", "we", "our", "us"})

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "average_sentence_words": round(average_sentence_words, 2),
        "sentence_length_cv": round(sentence_length_cv, 3),
        "unique_word_ratio": round(unique_word_ratio, 3),
        "template_phrase_count": phrase_hit_count,
        "template_phrase_density_per_100_words": round(phrase_hit_count / max(word_count, 1) * 100, 2),
        "template_phrases": phrase_hits,
        "structured_phrase_count": structured_phrase_count,
        "structured_phrase_density_per_100_words": round(structured_phrase_count / max(word_count, 1) * 100, 2),
        "structured_phrases": structured_phrase_hits,
        "filler_phrase_count": filler_phrase_count,
        "filler_phrase_density_per_100_words": round(filler_phrase_count / max(word_count, 1) * 100, 2),
        "filler_phrases": filler_phrase_hits,
        "transition_phrase_count": transition_phrase_count,
        "transition_phrase_density_per_100_words": round(transition_phrase_count / max(word_count, 1) * 100, 2),
        "transition_phrases": transition_phrase_hits,
        "generic_word_density_per_100_words": round(generic_word_density, 2),
        "abstract_word_count": abstract_word_count,
        "abstract_word_density_per_100_words": round(abstract_word_density, 2),
        "abstract_cluster_count": abstract_cluster_count,
        "suspicious_pattern_count": sum(suspicious_pattern_hits.values()),
        "suspicious_patterns": suspicious_pattern_hits,
        "repeated_trigram_ratio": round(repeated_trigram_ratio, 3),
        "sentence_start_repetition": round(sentence_start_repetition, 3),
        "concrete_marker_count": concrete_marker_count,
        "first_person_count": first_person_count,
    }


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

    # Paste "ratio" is shown as a percent in the UI, so clamp it to <= 100%.
    # We still keep total_pasted_chars as a separate metric for volume.
    paste_ratio = min(total_pasted_chars, total_chars) / max(total_chars, 1)
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
    category: str = "behavior",
) -> None:
    signals.append(
        {
            "direction": direction,
            "weight": weight,
            "label": label,
            "detail": detail,
            "category": category,
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


def score_content_patterns(text: str) -> Dict[str, Any]:
    features = extract_content_features(text)
    risk_score = 0
    signals: List[Dict[str, Any]] = []
    word_count = features["word_count"]

    if word_count < 80:
        add_signal(
            signals,
            direction="reassuring",
            weight=6,
            label="Short text caution",
            detail="The text is short, so content-pattern scoring is intentionally conservative.",
            category="content",
        )

    if word_count >= 120 and features["template_phrase_density_per_100_words"] >= 2.2:
        risk_score += 12
        add_signal(
            signals,
            direction="risk",
            weight=12,
            label="Overall template phrase density",
            detail=f"{features['template_phrase_count']} common template-style phrases were found in the text.",
            category="content",
        )
    elif word_count >= 120 and features["template_phrase_count"] >= 3:
        risk_score += 6
        add_signal(
            signals,
            direction="risk",
            weight=6,
            label="Repeated template-style phrasing",
            detail=f"{features['template_phrase_count']} template-style phrases were found.",
            category="content",
        )

    if word_count >= 120 and features["structured_phrase_count"] >= 2:
        risk_score += 14
        add_signal(
            signals,
            direction="risk",
            weight=14,
            label="Over-structured reasoning flow",
            detail=f"{features['structured_phrase_count']} balanced academic reasoning phrases were found.",
            category="content",
        )

    if word_count >= 120 and features["filler_phrase_count"] >= 2:
        risk_score += 12
        add_signal(
            signals,
            direction="risk",
            weight=12,
            label="Padding-style generalization",
            detail=f"{features['filler_phrase_count']} broad filler phrases were found without necessarily adding specific evidence.",
            category="content",
        )

    if word_count >= 120 and features["transition_phrase_count"] >= 3:
        risk_score += 8
        add_signal(
            signals,
            direction="risk",
            weight=8,
            label="Heavy flow-control transitions",
            detail=f"{features['transition_phrase_count']} smooth transition phrases were found.",
            category="content",
        )

    if word_count >= 120 and features["suspicious_pattern_count"] >= 2:
        risk_score += 18
        add_signal(
            signals,
            direction="risk",
            weight=18,
            label="Suspicious phrase and abstract-noun combinations",
            detail=f"{features['suspicious_pattern_count']} phrase-plus-abstract-word combinations were found.",
            category="content",
        )
    elif word_count >= 120 and features["suspicious_pattern_count"] == 1:
        risk_score += 9
        add_signal(
            signals,
            direction="risk",
            weight=9,
            label="Suspicious phrase and abstract-noun combination",
            detail="One phrase-plus-abstract-word combination was found.",
            category="content",
        )

    if word_count >= 150 and features["sentence_count"] >= 6:
        if features["sentence_length_cv"] <= 0.35:
            risk_score += 16
            add_signal(
                signals,
                direction="risk",
                weight=16,
                label="Unusually even sentence rhythm",
                detail="Sentence lengths are very uniform, which can indicate generated or heavily templated text.",
                category="content",
            )
        elif features["sentence_length_cv"] >= 0.75:
            risk_score -= 6
            add_signal(
                signals,
                direction="reassuring",
                weight=6,
                label="Varied sentence rhythm",
                detail="The writing contains a wider mix of short and long sentences.",
                category="content",
            )

    if word_count >= 150 and features["unique_word_ratio"] <= 0.42:
        risk_score += 12
        add_signal(
            signals,
            direction="risk",
            weight=12,
            label="Low lexical variety",
            detail=f"The unique-word ratio is {features['unique_word_ratio']}, suggesting repeated vocabulary.",
            category="content",
        )
    elif word_count >= 150 and features["unique_word_ratio"] >= 0.62:
        risk_score -= 5
        add_signal(
            signals,
            direction="reassuring",
            weight=5,
            label="Healthy lexical variety",
            detail=f"The unique-word ratio is {features['unique_word_ratio']}.",
            category="content",
        )

    if word_count >= 120 and features["abstract_word_density_per_100_words"] >= 5 and features["abstract_cluster_count"] >= 1:
        risk_score += 14
        add_signal(
            signals,
            direction="risk",
            weight=14,
            label="Clustered abstract vocabulary",
            detail=(
                f"Abstract academic words appear {features['abstract_word_density_per_100_words']} times per 100 words "
                f"across {features['abstract_cluster_count']} dense cluster(s)."
            ),
            category="content",
        )
    elif word_count >= 120 and features["abstract_word_density_per_100_words"] >= 4:
        risk_score += 8
        add_signal(
            signals,
            direction="risk",
            weight=8,
            label="High abstract vocabulary density",
            detail=f"Abstract academic words appear {features['abstract_word_density_per_100_words']} times per 100 words.",
            category="content",
        )

    if word_count >= 150 and features["repeated_trigram_ratio"] >= 0.055:
        risk_score += 12
        add_signal(
            signals,
            direction="risk",
            weight=12,
            label="Repeated phrase patterns",
            detail="Several three-word phrases recur across the submission.",
            category="content",
        )

    if features["sentence_count"] >= 6 and features["sentence_start_repetition"] >= 0.45:
        risk_score += 8
        add_signal(
            signals,
            direction="risk",
            weight=8,
            label="Repeated sentence openings",
            detail="Many sentences begin with the same first two words.",
            category="content",
        )

    if word_count >= 120 and features["concrete_marker_count"] >= 3:
        risk_score -= 8
        add_signal(
            signals,
            direction="reassuring",
            weight=8,
            label="Concrete supporting details",
            detail="The text includes details such as numbers, quoted material, or citation-style references.",
            category="content",
        )
    elif word_count >= 180 and features["concrete_marker_count"] == 0:
        risk_score += 8
        add_signal(
            signals,
            direction="risk",
            weight=8,
            label="Limited concrete detail",
            detail="The submission has no numbers, quotes, or citation-style markers.",
            category="content",
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
        "features": features,
        "disclaimer": (
            "Content-pattern analysis is a heuristic support signal. It cannot prove AI authorship "
            "and should be reviewed with the behavior evidence."
        ),
    }


def build_combined_summary(
    combined_score: int,
    combined_level: str,
    behavior_score: int,
    content_score: int,
) -> str:
    if combined_level == "high":
        if behavior_score >= 60 and content_score >= 40:
            return (
                "High-risk combined pattern: both the writing behavior and final text patterns "
                "show indicators that need manual review."
            )
        return "High-risk combined pattern: the behavior evidence is the strongest concern."

    if combined_level == "moderate":
        if content_score >= behavior_score:
            return (
                "Moderate-risk combined pattern: the final text contains content-pattern signals, "
                "but this should be checked against the writing behavior before any conclusion."
            )
        return "Moderate-risk combined pattern: the main concern comes from the writing behavior log."

    return (
        "Low-risk combined pattern. No strong suspicious pattern was detected across behavior "
        "and content signals."
    )


def combine_analysis_scores(behavior_score: int, content_score: int) -> Dict[str, Any]:
    combined_score = behavior_score * 0.7 + content_score * 0.3

    if behavior_score >= 60 and content_score >= 45:
        combined_score += 8
    elif behavior_score <= 25 and content_score >= 45:
        combined_score -= 6
    elif behavior_score <= 25 and content_score <= 20:
        combined_score -= 4

    combined_score = round(clamp(combined_score, 0, 100))
    combined_level = classify_risk(combined_score)

    return {
        "risk_score": combined_score,
        "risk_level": combined_level,
        "summary": build_combined_summary(
            combined_score,
            combined_level,
            behavior_score,
            content_score,
        ),
    }


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


def extract_paste_sections(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    paste_sections: List[Dict[str, Any]] = []

    for index, event in enumerate(events):
        if safe_event_type(event) != "paste":
            continue

        snippet_value = event.get("snippet", "")
        snippet = snippet_value if isinstance(snippet_value, str) else ""
        snippet = re.sub(r"\s+", " ", snippet).strip()
        if len(snippet) > 180:
            snippet = f"{snippet[:177]}..."

        section_value = event.get("target_section", "")
        target_section = section_value if isinstance(section_value, str) else ""
        paste_sections.append(
            {
                "id": f"paste_{index + 1}",
                "length_chars": max(safe_int(event.get("length")), 0),
                "word_count": max(safe_int(event.get("words")), 0),
                "time": max(safe_int(event.get("time")), 0),
                "target_section": target_section,
                "snippet": snippet,
            }
        )

    return paste_sections


def extract_flagged_sections(text: str) -> List[Dict[str, Any]]:
    flagged_sections: List[Dict[str, Any]] = []
    sentences = split_sentences(text)

    for index, sentence in enumerate(sentences):
        normalized = re.sub(r"\s+", " ", sentence.lower())
        reasons: List[str] = []

        matching_phrases = [phrase for phrase in AI_STYLE_PHRASES if phrase in normalized]
        if matching_phrases:
            reasons.append(f"Template-style phrasing: {', '.join(matching_phrases[:2])}")

        for phrase, abstract_word in SUSPICIOUS_PATTERNS:
            if phrase in normalized and re.search(rf"\b{re.escape(abstract_word)}s?\b", normalized):
                reasons.append(f"Suspicious pattern: '{phrase}' with '{abstract_word}'")

        sentence_words = tokenize_words(sentence)
        abstract_hits = [word for word in sentence_words if word in ABSTRACT_WORDS]
        if len(abstract_hits) >= 3:
            reasons.append("Dense abstract vocabulary in a single sentence")

        if reasons:
            excerpt = sentence.strip()
            if len(excerpt) > 240:
                excerpt = f"{excerpt[:237]}..."

            flagged_sections.append(
                {
                    "section_index": index + 1,
                    "text_excerpt": excerpt,
                    "reasons": reasons[:3],
                }
            )

    return flagged_sections[:12]


def analyze_submission(sub: Submission) -> Dict[str, Any]:
    features = extract_features(sub)
    behavior_scoring = score_submission(features)
    content_scoring = score_content_patterns(sub.text or "")
    combined_scoring = combine_analysis_scores(
        behavior_scoring["risk_score"],
        content_scoring["risk_score"],
    )
    metrics = build_metric_summary(features)
    combined_signals = behavior_scoring["signals"] + content_scoring["signals"]
    combined_signals.sort(key=lambda signal: signal["weight"], reverse=True)
    combined_reasons = [signal["label"] for signal in combined_signals if signal["direction"] == "risk"][:5]

    response = {
        "risk": combined_scoring["risk_score"],
        "risk_score": combined_scoring["risk_score"],
        "risk_level": combined_scoring["risk_level"],
        "summary": combined_scoring["summary"],
        "reasons": combined_reasons,
        "signals": combined_signals,
        "metrics": metrics,
        "features": features,
        "behavior_analysis": {
            "risk_score": behavior_scoring["risk_score"],
            "risk_level": behavior_scoring["risk_level"],
            "summary": behavior_scoring["summary"],
            "reasons": behavior_scoring["reasons"],
            "signals": behavior_scoring["signals"],
            "features": features,
        },
        "content_analysis": content_scoring,
        "analysis_note": (
            "The combined score gives more weight to writing behavior than text content. "
            "Content-pattern analysis is only a support signal and cannot prove AI authorship."
        ),
    }

    return response


@app.post("/submit")
def receive_submission(sub: Submission) -> Dict[str, Any]:
    response = analyze_submission(sub)

    print("\n--- New Submission ---")
    print("Words:", sub.total_words)
    print("Duration:", sub.duration_seconds, "seconds")
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

    return response


@app.get("/assignments/public")
def get_public_assignments() -> Dict[str, Any]:
    assignment_list = sorted(
        ASSIGNMENTS.values(),
        key=lambda item: item["created_at"],
        reverse=True,
    )
    return {
        "assignments": [
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
    }


@app.post("/teacher/assignments")
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

    assignment_id = make_id("asg")
    assignment = {
        "id": assignment_id,
        "title": title,
        "description": description,
        "due_date": due_date,
        "max_score": max(payload.max_score, 1),
        "created_at": now_iso(),
        "submission_ids": [],
    }
    ASSIGNMENTS[assignment_id] = assignment
    return assignment


@app.get("/teacher/assignments")
def get_teacher_assignments() -> Dict[str, Any]:
    assignment_rows: List[Dict[str, Any]] = []
    for assignment in sorted(ASSIGNMENTS.values(), key=lambda item: item["created_at"], reverse=True):
        scores = [
            SUBMISSIONS[submission_id]["analysis"]["risk_score"]
            for submission_id in assignment["submission_ids"]
            if submission_id in SUBMISSIONS
        ]
        assignment_rows.append(
            {
                **assignment,
                "submission_count": len(assignment["submission_ids"]),
                "average_risk_score": round(sum(scores) / len(scores), 1) if scores else None,
            }
        )

    return {"assignments": assignment_rows}


@app.post("/assignments/{assignment_id}/submit")
def submit_assignment(assignment_id: str, payload: StudentSubmissionRequest) -> Dict[str, Any]:
    assignment = ASSIGNMENTS.get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    sub = Submission(
        text=payload.text,
        total_chars=payload.total_chars,
        total_words=payload.total_words,
        startTime=payload.startTime,
        endTime=payload.endTime,
        duration_seconds=payload.duration_seconds,
        events=payload.events,
    )
    analysis = analyze_submission(sub)
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

    SUBMISSIONS[submission_id] = submission_record
    assignment["submission_ids"].append(submission_id)

    return {
        "status": "submitted",
        "message": "Submission received and sent to teacher dashboard for review.",
        "submission_id": submission_id,
        "assignment_id": assignment_id,
    }


@app.get("/teacher/assignments/{assignment_id}/submissions")
def get_assignment_submissions(assignment_id: str) -> Dict[str, Any]:
    assignment = ASSIGNMENTS.get(assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")

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
        for submission in [SUBMISSIONS.get(submission_id)]
        if submission is not None
    ]

    submissions.sort(key=lambda item: item["submitted_at"], reverse=True)
    return {"assignment": assignment, "submissions": submissions}


@app.get("/teacher/submissions/{submission_id}")
def get_submission_detail(submission_id: str) -> Dict[str, Any]:
    submission = SUBMISSIONS.get(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    return submission
