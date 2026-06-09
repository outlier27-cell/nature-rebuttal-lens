"""Kant-style universalization checks for RebuttalLens response cards."""

from __future__ import annotations

from enum import Enum
import re
from typing import Any


class UniversalizationDecision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    DEFER = "defer"


class UniversalizationResult(dict):
    """Dict-compatible universalization result with a stable to_dict method."""

    def __init__(self, **kwargs: Any):
        super().__init__(kwargs)
        self.__dict__ = self

    def to_dict(self) -> dict[str, Any]:
        return dict(self)


ALLOWED_ACTIONS = {
    "SOFTEN_CLAIM",
    "CLARIFY_EXISTING",
    "ACCEPT_ANALYSIS",
    "ACCEPT_TEXT",
}

DECEPTIVE_PATTERNS = [
    r"\bexaggerat(?:e|es|ed|ing|ion)\b",
    r"\boverstate\b",
    r"\boverstated\b",
    r"\boverstating\b",
    r"\bhide\b.*\blimitation\b",
    r"\blimitation\b.*\bhide\b",
    r"\bconceal\b.*\blimitation\b",
    r"\bfabricat(?:e|es|ed|ing|ion)\b",
    r"\bmake\s+up\b",
    r"\bmade\s+up\b",
    r"\bpretend\b",
]


def check_universalization(
    card: dict[str, Any] | None = None,
    *,
    action_text: str = "",
    proposed_action: str = "",
    readiness: str = "",
    risk_level: str = "",
) -> UniversalizationResult:
    """Return an auditable allow/warn/block/defer decision for one suggestion."""
    response_card = dict(card or {})
    if proposed_action:
        response_card["proposed_action"] = proposed_action
    if readiness:
        response_card["readiness"] = readiness
    if risk_level:
        response_card["risk_level"] = risk_level
    if action_text:
        response_card["suggestion"] = action_text
    proposed_action = str(response_card.get("proposed_action") or "").strip().upper()
    readiness = str(response_card.get("readiness") or "").strip().lower()
    risk_level = str(response_card.get("risk_level") or "").strip().lower()
    suggestion_text = _card_text(response_card)

    if _contains_deceptive_suggestion(suggestion_text):
        decision = UniversalizationDecision.BLOCK
        principle = "A rebuttal assistant must not improve persuasion by weakening truthfulness."
        effect = (
            "Academic review would become less reliable because unsupported claims would be "
            "made more persuasive instead of more verifiable."
        )
        reason = "The recommendation asks the author to overclaim, conceal, or fabricate support."
        universalizable: bool | None = False
        requires_author_decision = False
    elif readiness == "decision_deferred" or (
        proposed_action == "AUTHOR_INPUT_NEEDED" and risk_level in {"high", "blocking"}
    ):
        decision = UniversalizationDecision.DEFER
        principle = "High-risk scholarly commitments must remain author-confirmed decisions."
        effect = (
            "Academic review becomes more conservative but also more auditable and verifiable."
        )
        reason = "A high-risk author decision must be renewed by the author instead of automated."
        universalizable = True
        requires_author_decision = True
    elif proposed_action in ALLOWED_ACTIONS:
        decision = UniversalizationDecision.ALLOW
        principle = "Rebuttal support should make claims narrower, clearer, or better evidenced."
        effect = "Academic review would become more traceable and less dependent on rhetoric."
        reason = "The bounded action can be generalized as transparent assistance."
        universalizable = True
        requires_author_decision = False
    else:
        decision = UniversalizationDecision.WARN
        principle = "Recommendations must remain bounded by evidence and author verification."
        effect = "Academic review may benefit, but the author must verify the evidential basis."
        reason = "The action is not blocked, but it needs human review before being treated as a norm."
        universalizable = None
        requires_author_decision = proposed_action == "AUTHOR_INPUT_NEEDED"

    return UniversalizationResult(
        comment_id=str(
            response_card.get("comment_id") or response_card.get("concern_id") or ""
        ),
        proposed_action=proposed_action,
        readiness=readiness,
        risk_level=risk_level,
        decision=decision.value,
        universalizable=universalizable,
        requires_author_decision=requires_author_decision,
        principle=principle,
        universalized_world=_universalized_world(decision),
        academic_process_effect=effect,
        ethical_block_reason=(
            reason
            if decision in {UniversalizationDecision.BLOCK, UniversalizationDecision.DEFER}
            else ""
        ),
        reason=reason,
    )


def _contains_deceptive_suggestion(text: str) -> bool:
    checked_text = _strip_safety_constraints(text)
    return any(
        re.search(pattern, checked_text, flags=re.IGNORECASE)
        for pattern in DECEPTIVE_PATTERNS
    )


def _strip_safety_constraints(text: str) -> str:
    """Remove local "avoid/do not X" safety clauses before deception matching."""
    unsafe_terms = (
        r"exaggerat(?:e|es|ed|ing|ion)|"
        r"overstat(?:e|es|ed|ing)|"
        r"hide\b[^.?!;]{0,40}\blimitation|"
        r"limitation\b[^.?!;]{0,40}\bhide|"
        r"conceal\b[^.?!;]{0,40}\blimitation|"
        r"fabricat(?:e|es|ed|ing|ion)|"
        r"make\s+up|made\s+up|pretend"
    )
    safety_clause = re.compile(
        rf"\b(?:avoid|do\s+not|don't|must\s+not|should\s+not|never)\b"
        rf"[^.?!;]{{0,120}}\b(?:{unsafe_terms})\b[^.?!;]*",
        flags=re.IGNORECASE,
    )
    return safety_clause.sub(" ", text)


def _card_text(card: dict[str, Any]) -> str:
    fields = [
        "suggestion",
        "draft_text",
        "rationale",
        "required_artifact",
        "recommended_action",
        "safe_response_language",
        "missing_author_input",
        "memory_decision_boundary",
    ]
    return " ".join(str(card.get(field, "")) for field in fields)


def _universalized_world(decision: UniversalizationDecision) -> str:
    if decision == UniversalizationDecision.BLOCK:
        return (
            "If all review-response assistants recommended this action, authors would be "
            "encouraged to replace evidence with rhetorical force."
        )
    if decision == UniversalizationDecision.DEFER:
        return (
            "If all assistants deferred this class of commitment, fields would receive fewer "
            "unsupported promises and more explicit author accountability."
        )
    if decision == UniversalizationDecision.ALLOW:
        return (
            "If all assistants followed this rule, rebuttals would connect claims to evidence "
            "more explicitly."
        )
    return (
        "If all assistants used this uncertain recommendation, some outputs could become useful "
        "but unevenly grounded."
    )
