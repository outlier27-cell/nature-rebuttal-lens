from typing import Any

from peer_review_skills.schemas.annotation import AuthorAnnotation, ReviewerAnnotation


ANNOTATION_METHOD = "rule_based_v1"


REVIEWER_RULES = (
    ("baseline_comparison", "baseline", ("baseline", "sota", "state-of-the-art", "comparison", "compare")),
    ("ablation_mechanism", "ablation", ("ablation", "mechanism", "feature importance", "shap")),
    ("reproducibility_reporting", "data_code", ("code", "github", "data availability", "dataset", "reproduc", "zenodo")),
    ("statistics_significance", "statistics", ("statistical", "significance", "p-value", "confidence interval", "sample size")),
    ("generalization_scope", "scope", ("generaliz", "external validation", "other dataset", "robust", "transfer")),
    ("experimental_design", "experiment", ("experiment", "validation", "prospective", "control", "wet-lab")),
    ("dataset_bias_ethics_safety", "clarification", ("bias", "ethic", "safety", "privacy", "fairness")),
    ("novelty_positioning", "clarification", ("novel", "novelty", "incremental", "contribution")),
    ("clarity_presentation", "clarification", ("clarify", "unclear", "figure", "legend", "typo", "readability")),
    ("theoretical_validity", "clarification", ("theoretical", "assumption", "causal", "validity")),
)

AUTHOR_RULES = (
    ("add_new_experiment", "experiment", ("new experiment", "additional experiment", "we performed", "we conducted", "wet-lab")),
    ("add_new_analysis", "analysis", ("additional analysis", "new analysis", "we analyzed", "we re-analyzed", "ablation")),
    ("acknowledge_and_fix", "text_revision", ("we agree", "we have revised", "we added", "we corrected", "we updated")),
    ("clarify_existing_evidence", "text_revision", ("we clarify", "we have clarified", "to clarify", "we explain")),
    ("narrow_claim_scope", "text_revision", ("we toned down", "we narrowed", "we revised the claim", "we removed")),
    ("contest_reviewer_premise", "none", ("we disagree", "not applicable", "we respectfully disagree")),
    ("defer_future_work", "none", ("future work", "beyond the scope", "in future studies")),
    ("justify_method_choice", "text_revision", ("we chose", "we used", "because", "rationale")),
    ("reframe_contribution", "text_revision", ("we emphasize", "we reframed", "we now highlight")),
    ("editorial_only_change", "text_revision", ("typo", "grammar", "format", "figure legend")),
)


def _matches(text: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def _claim(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:240]


def _reviewer_sentiment_and_severity(text: str, matched_keywords: list[str]) -> tuple[str, str]:
    lowered = text.lower()
    if any(phrase in lowered for phrase in ("not suitable", "major concern", "fatal", "serious", "unacceptable")):
        return "strongly_critical", "blocking"
    if any(phrase in lowered for phrase in ("insufficient", "weak", "concern", "lack", "missing", "unclear")):
        return "critical", "major" if matched_keywords else "moderate"
    if any(phrase in lowered for phrase in ("please", "could", "should", "suggest")):
        return "skeptical", "moderate"
    if any(phrase in lowered for phrase in ("well written", "interesting", "strong", "valuable")):
        return "supportive", "minor"
    return "neutral", "unknown"


def _author_stance(text: str) -> str:
    lowered = text.lower()
    if "respectfully disagree" in lowered or "we disagree" in lowered:
        return "disagree"
    if any(phrase in lowered for phrase in ("partially", "in part", "while we agree")):
        return "partial"
    if any(phrase in lowered for phrase in ("we agree", "thank", "appreciate", "as suggested")):
        return "agree"
    return "neutral"


def _scope_adjustment(text: str) -> str:
    lowered = text.lower()
    if any(phrase in lowered for phrase in ("narrow", "toned down", "removed the claim", "limit our claim")):
        return "narrowed"
    if any(phrase in lowered for phrase in ("expanded", "broadened", "extended")):
        return "expanded"
    return "none"


def annotate_reviewer_unit(unit: dict[str, Any]) -> ReviewerAnnotation:
    text = str(unit.get("text") or "")
    matched_rule = ("unknown", "unknown", [])
    for concern_type, evidence_request, keywords in REVIEWER_RULES:
        hits = _matches(text, keywords)
        if hits:
            matched_rule = (concern_type, evidence_request, hits)
            break
    concern_type, evidence_request, matched_keywords = matched_rule
    evidence_request = _infer_evidence_request(text, evidence_request)
    sentiment, severity = _reviewer_sentiment_and_severity(text, matched_keywords)
    confidence = 0.78 if concern_type != "unknown" else 0.42
    if severity in {"blocking", "major"} and concern_type != "unknown":
        confidence += 0.05
    return ReviewerAnnotation(
        annotation_id=f"{unit['unit_id']}:reviewer_annotation",
        unit_id=unit["unit_id"],
        paper_id=unit["paper_id"],
        concern_type=concern_type,
        concern_claim=_claim(text),
        evidence_request=evidence_request,
        reviewer_sentiment=sentiment,
        reviewer_severity=severity,
        confidence=min(confidence, 0.95),
        annotation_method=ANNOTATION_METHOD,
        matched_keywords=matched_keywords,
        source_trace=dict(unit.get("source_trace") or {}),
    )


def _infer_evidence_request(text: str, default: str) -> str:
    lowered = text.lower()
    evidence_rules = (
        ("ablation", ("ablation",)),
        ("baseline", ("baseline", "sota", "state-of-the-art", "comparison")),
        ("experiment", ("experiment", "validation", "control", "prospective")),
        ("statistics", ("statistical", "significance", "p-value", "confidence interval", "sample size")),
        ("data_code", ("code", "github", "dataset", "data availability", "zenodo")),
        ("scope", ("generaliz", "external validation", "other dataset")),
        ("clarification", ("clarify", "unclear", "explain")),
    )
    for evidence, keywords in evidence_rules:
        if any(keyword in lowered for keyword in keywords):
            return evidence
    return default


def annotate_author_unit(unit: dict[str, Any]) -> AuthorAnnotation:
    text = str(unit.get("text") or "")
    matched_rule = ("unknown", "unknown", [])
    for strategy, evidence_supplied, keywords in AUTHOR_RULES:
        hits = _matches(text, keywords)
        if hits:
            matched_rule = (strategy, evidence_supplied, hits)
            break
    strategy, evidence_supplied, matched_keywords = matched_rule
    confidence = 0.8 if strategy != "unknown" else 0.4
    return AuthorAnnotation(
        annotation_id=f"{unit['unit_id']}:author_annotation",
        unit_id=unit["unit_id"],
        paper_id=unit["paper_id"],
        author_strategy=strategy,
        author_action=_claim(text),
        response_stance=_author_stance(text),
        evidence_supplied=evidence_supplied,
        scope_adjustment=_scope_adjustment(text),
        confidence=confidence,
        annotation_method=ANNOTATION_METHOD,
        matched_keywords=matched_keywords,
        source_trace=dict(unit.get("source_trace") or {}),
    )


def annotate_review_unit(unit: dict[str, Any]) -> ReviewerAnnotation | AuthorAnnotation | None:
    speaker = unit.get("speaker_type")
    if speaker == "reviewer":
        return annotate_reviewer_unit(unit)
    if speaker == "author":
        return annotate_author_unit(unit)
    return None
