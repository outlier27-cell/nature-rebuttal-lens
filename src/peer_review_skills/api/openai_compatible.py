import json
import shutil
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from peer_review_skills.io.jsonl import read_jsonl, write_jsonl
from peer_review_skills.taxonomy.pipeline import CONCERN_LABELS, RESPONSE_STRATEGY_LABELS


Transport = Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]]


class OpenAICompatibleChatClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        transport: Transport | None = None,
        timeout_seconds: int = 120,
        timeout_retry_count: int = 1,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.transport = transport or _urllib_transport
        self.timeout_seconds = timeout_seconds
        self.timeout_retry_count = timeout_retry_count

    def __repr__(self) -> str:
        return (
            f"OpenAICompatibleChatClient(base_url={self.base_url!r}, "
            f"model={self.model!r}, api_key=<redacted>)"
        )

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = _chat_completions_url(self.base_url)
        try:
            raw_response = self._send_request(url, headers, payload)
        except RuntimeError as exc:
            if response_format is None or not _is_response_format_rejection(str(exc)):
                raise
            fallback_payload = dict(payload)
            fallback_payload.pop("response_format", None)
            raw_response = self._send_request(url, headers, fallback_payload)
        return _normalize_chat_response(raw_response)

    def _send_request(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        attempts = self.timeout_retry_count + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                return self.transport(url, headers, payload, self.timeout_seconds)
            except Exception as exc:  # noqa: BLE001 - transport must preserve provider errors.
                last_error = exc
                if attempt >= self.timeout_retry_count or not _is_timeout_error(str(exc)):
                    raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("API request failed before any transport attempt completed")


def execute_api_handoff(
    project_root: str | Path,
    client: Any,
    *,
    limit: int | None = None,
    scope: str = "mvp",
) -> dict[str, Any]:
    root = Path(project_root)
    handoff_dir = root / "data/evaluation/api_handoff"
    result_dir = root / "data/evaluation/api_results"
    scoped_result_dir = result_dir / scope
    alignment_requests = _read_scoped_optional_jsonl(
        handoff_dir,
        scope,
        "alignment_requests.jsonl",
    )
    skill_requests = _read_scoped_optional_jsonl(
        handoff_dir,
        scope,
        "skill_enrichment_requests.jsonl",
    )
    existing_alignment_results = _read_scoped_optional_jsonl(result_dir, scope, "alignment_results.jsonl")
    existing_skill_results = _read_scoped_optional_jsonl(result_dir, scope, "skill_enrichment_results.jsonl")
    existing_alignment_ids = {
        str(result.get("request_id"))
        for result in existing_alignment_results
        if result.get("request_id") and not result.get("error")
    }
    existing_skill_ids = {
        str(result.get("request_id"))
        for result in existing_skill_results
        if result.get("request_id") and not result.get("error")
    }
    alignment_requests, skipped_alignment_count = _pending_api_requests(
        alignment_requests,
        existing_alignment_ids,
    )
    skill_requests, skipped_skill_count = _pending_api_requests(
        skill_requests,
        existing_skill_ids,
    )
    skipped_existing_result_count = skipped_alignment_count + skipped_skill_count
    selected_requests = _limit_requests(
        [("alignment", request) for request in alignment_requests]
        + [("skill_enrichment", request) for request in skill_requests],
        limit,
    )

    alignment_results: list[dict[str, Any]] = []
    skill_results: list[dict[str, Any]] = []
    error_results: list[dict[str, Any]] = []

    for queue_name, request in selected_requests:
        try:
            if queue_name == "alignment":
                alignment_results.append(_execute_alignment_request(client, request))
            else:
                skill_results.append(_execute_skill_enrichment_request(client, request))
        except Exception as exc:  # noqa: BLE001 - queue execution must keep per-request errors.
            error_results.append(
                {
                    "request_id": request.get("request_id"),
                    "task_type": request.get("task_type"),
                    "error": str(exc),
                }
            )

    merged_alignment_results = _merge_api_result_records(existing_alignment_results, alignment_results)
    merged_skill_results = _merge_api_result_records(existing_skill_results, skill_results)
    write_jsonl(scoped_result_dir / "alignment_results.jsonl", merged_alignment_results)
    write_jsonl(scoped_result_dir / "skill_enrichment_results.jsonl", merged_skill_results)
    write_jsonl(scoped_result_dir / "api_errors.jsonl", error_results)
    write_jsonl(result_dir / "alignment_results.jsonl", merged_alignment_results)
    write_jsonl(result_dir / "skill_enrichment_results.jsonl", merged_skill_results)
    write_jsonl(result_dir / "api_errors.jsonl", error_results)

    summary = {
        "alignment_result_count": len(alignment_results),
        "skill_enrichment_result_count": len(skill_results),
        "cumulative_alignment_result_count": len(merged_alignment_results),
        "cumulative_skill_enrichment_result_count": len(merged_skill_results),
        "error_count": len(error_results),
        "processed_count": len(selected_requests),
        "queued_alignment_request_count": len(alignment_requests),
        "queued_skill_enrichment_request_count": len(skill_requests),
        "skipped_existing_result_count": skipped_existing_result_count,
        "limit": limit,
        "scope": scope,
    }
    report_path = root / "data/evaluation/reports/api_execution_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_api_execution_report(summary), encoding="utf-8", newline="\n")
    return summary


def render_api_execution_report(summary: dict[str, Any]) -> str:
    return (
        "# API Execution Report\n\n"
        "## Summary\n\n"
        f"- Processed request count: {summary['processed_count']}\n"
        f"- New alignment result count: {summary['alignment_result_count']}\n"
        f"- New skill enrichment result count: {summary['skill_enrichment_result_count']}\n"
        f"- Cumulative alignment result count: {summary['cumulative_alignment_result_count']}\n"
        f"- Cumulative skill enrichment result count: {summary['cumulative_skill_enrichment_result_count']}\n"
        f"- Error count: {summary['error_count']}\n"
        f"- Queued alignment request count: {summary['queued_alignment_request_count']}\n"
        f"- Queued skill enrichment request count: {summary['queued_skill_enrichment_request_count']}\n"
        f"- Limit: {summary['limit'] if summary.get('limit') is not None else 'none'}\n"
    )


def apply_api_results(project_root: str | Path, *, scope: str = "mvp") -> dict[str, Any]:
    root = Path(project_root)
    result_dir = root / "data/evaluation/api_results"
    scoped_result_dir = result_dir / scope
    resolved_dir = root / "data/processed/api_resolved"
    interactions = _read_optional_jsonl(root / "data/processed/interaction_units/interaction_units.jsonl")
    alignment_results = _read_scoped_optional_jsonl(result_dir, scope, "alignment_results.jsonl")
    skill_results = _read_scoped_optional_jsonl(result_dir, scope, "skill_enrichment_results.jsonl")
    alignment_by_interaction = {
        str(result.get("interaction_id")): result
        for result in alignment_results
        if result.get("interaction_id")
    }
    skill_by_id = {
        str(result.get("skill_id")): result
        for result in skill_results
        if result.get("skill_id")
    }

    merge_errors: list[dict[str, Any]] = []
    resolved_interactions = []
    resolved_alignment_count = 0
    for interaction in interactions:
        result = alignment_by_interaction.get(str(interaction.get("interaction_id")))
        if result is None:
            resolved_interactions.append(interaction)
            continue
        resolved, error = _apply_alignment_result(interaction, result)
        if error is not None:
            merge_errors.append(error)
            resolved_interactions.append(interaction)
        else:
            resolved_interactions.append(resolved)
            resolved_alignment_count += 1

    write_jsonl(resolved_dir / "interaction_units.jsonl", resolved_interactions)

    original_skill_dir = root / "data/processed/skill_cards" / scope
    resolved_skill_dir = resolved_dir / "skill_cards" / scope
    enriched_skill_count = 0
    if original_skill_dir.exists():
        resolved_skill_dir.mkdir(parents=True, exist_ok=True)
        for old_card in resolved_skill_dir.glob("*.json"):
            old_card.unlink()
        for path in sorted(original_skill_dir.glob("*.json")):
            card = json.loads(path.read_text(encoding="utf-8"))
            result = skill_by_id.get(str(card.get("skill_id")))
            if result is not None:
                card = _apply_skill_result(card, result)
                enriched_skill_count += 1
            (resolved_skill_dir / path.name).write_text(
                json.dumps(card, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
    elif original_skill_dir.parent.exists():
        shutil.copytree(original_skill_dir.parent, resolved_skill_dir.parent, dirs_exist_ok=True)

    write_jsonl(scoped_result_dir / "api_merge_errors.jsonl", merge_errors)
    write_jsonl(result_dir / "api_merge_errors.jsonl", merge_errors)
    summary = {
        "resolved_alignment_count": resolved_alignment_count,
        "enriched_skill_count": enriched_skill_count,
        "merge_error_count": len(merge_errors),
        "alignment_result_count": len(alignment_results),
        "skill_enrichment_result_count": len(skill_results),
    }
    report_path = root / "data/evaluation/reports/api_apply_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_api_apply_report(summary), encoding="utf-8", newline="\n")
    return summary


def render_api_apply_report(summary: dict[str, Any]) -> str:
    return (
        "# API Apply Report\n\n"
        "## Summary\n\n"
        f"- Resolved alignment count: {summary['resolved_alignment_count']}\n"
        f"- Enriched skill count: {summary['enriched_skill_count']}\n"
        f"- Merge error count: {summary['merge_error_count']}\n"
        f"- Alignment result count: {summary['alignment_result_count']}\n"
        f"- Skill enrichment result count: {summary['skill_enrichment_result_count']}\n"
    )


def extract_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    candidates = [stripped]
    if fenced:
        candidates.insert(0, fenced.group(1).strip())
    candidates.extend(_json_object_candidates(stripped))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("model response did not contain a JSON object")


def _json_object_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for start, char in enumerate(text):
        if char != "{":
            continue
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            current = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start : index + 1])
                    break
    return candidates


def build_client_from_environment(env: dict[str, str] | None = None) -> OpenAICompatibleChatClient:
    import os
    from peer_review_skills.agents.providers import (
        DEFAULT_OPENAI_COMPATIBLE_BASE_URL,
        DEFAULT_OPENAI_COMPATIBLE_MODEL,
    )

    environment = env if env is not None else os.environ
    base_url = environment.get("PEER_REVIEW_API_BASE_URL", DEFAULT_OPENAI_COMPATIBLE_BASE_URL).strip()
    api_key = environment.get("PEER_REVIEW_API_KEY", "").strip()
    model = environment.get("PEER_REVIEW_API_MODEL", DEFAULT_OPENAI_COMPATIBLE_MODEL).strip()
    timeout_seconds = _read_timeout_seconds(environment)
    missing = [
        name
        for name, value in (
            ("PEER_REVIEW_API_BASE_URL", base_url),
            ("PEER_REVIEW_API_KEY", api_key),
            ("PEER_REVIEW_API_MODEL", model),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"missing API environment variables: {', '.join(missing)}")
    return OpenAICompatibleChatClient(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
    )


def _execute_alignment_request(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    result = client.create_chat_completion(
        _alignment_messages(request),
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    required = {"alignment_status", "selected_author_unit_ids", "rationale", "confidence"}
    _require_fields(result, required)
    if not isinstance(result["selected_author_unit_ids"], list):
        raise ValueError("field selected_author_unit_ids must be a list")
    return {
        "request_id": request.get("request_id"),
        "task_type": request.get("task_type"),
        "interaction_id": request.get("interaction_id"),
        "paper_id": request.get("paper_id"),
        "alignment_status": result["alignment_status"],
        "selected_author_unit_ids": result["selected_author_unit_ids"],
        "rationale": result["rationale"],
        "confidence": float(result["confidence"]),
    }


def _execute_skill_enrichment_request(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    result = client.create_chat_completion(
        _skill_enrichment_messages(request),
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    required = {"concern_type", "recommended_response_strategies", "rationale", "confidence"}
    _require_fields(result, required)
    if not isinstance(result["recommended_response_strategies"], list):
        raise ValueError("field recommended_response_strategies must be a list")
    return {
        "request_id": request.get("request_id"),
        "task_type": request.get("task_type"),
        "skill_id": request.get("skill_id"),
        "concern_type": result["concern_type"],
        "recommended_response_strategies": result["recommended_response_strategies"],
        "rationale": result["rationale"],
        "confidence": float(result["confidence"]),
    }


def _apply_alignment_result(
    interaction: dict[str, Any],
    result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    interaction_id = str(interaction.get("interaction_id") or "")
    selected_ids = [str(unit_id) for unit_id in result.get("selected_author_unit_ids", [])]
    candidate_ids = {str(unit_id) for unit_id in interaction.get("author_unit_ids", [])}
    if any(unit_id not in candidate_ids for unit_id in selected_ids):
        return (
            interaction,
            {
                "artifact_type": "interaction_unit",
                "artifact_id": interaction_id,
                "request_id": result.get("request_id"),
                "issue": "selected_author_unit_id_outside_candidate_context",
                "selected_author_unit_ids": selected_ids,
                "candidate_author_unit_ids": sorted(candidate_ids),
            },
        )
    resolved = dict(interaction)
    status = str(result.get("alignment_status") or interaction.get("alignment_status"))
    confidence = float(result.get("confidence", interaction.get("alignment_confidence", 0.0)))
    resolved["alignment_status"] = status
    resolved["alignment_confidence"] = confidence
    resolved["alignment_method"] = "api_semantic_resolution"
    if selected_ids:
        resolved["author_unit_ids"] = selected_ids
    source_trace = dict(resolved.get("source_trace") or {})
    source_trace["author_unit_ids"] = resolved.get("author_unit_ids", [])
    source_trace["api_resolution"] = {
        "request_id": result.get("request_id"),
        "rationale": result.get("rationale", ""),
        "confidence": confidence,
    }
    resolved["source_trace"] = source_trace
    return resolved, None


def _apply_skill_result(card: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(card)
    canonical_concern_type = _canonical_concern_type(
        str(result.get("concern_type") or ""),
        fallback=_skill_concern_type_from_id(str(card.get("skill_id") or "")),
    )
    canonical_strategies = _canonical_response_strategies(
        [str(strategy) for strategy in result.get("recommended_response_strategies", [])],
        fallback=enriched.get("recommended_response_strategies", []),
    )
    if canonical_strategies:
        enriched["recommended_response_strategies"] = canonical_strategies
    enriched["api_semantic_enrichment"] = {
        "request_id": result.get("request_id"),
        "concern_type": result.get("concern_type"),
        "canonical_concern_type": canonical_concern_type,
        "canonical_recommended_response_strategies": canonical_strategies,
        "rationale": result.get("rationale", ""),
        "confidence": float(result.get("confidence", 0.0)),
    }
    if float(result.get("confidence", 0.0)) >= 0.7:
        enriched["review_recommendation"] = "ready_for_api_enrichment"
    notes = str(enriched.get("notes") or "")
    if "API semantic enrichment applied." not in notes:
        enriched["notes"] = (notes + " API semantic enrichment applied.").strip()
    return enriched


def _canonical_concern_type(value: str, fallback: str = "unknown") -> str:
    normalized = _normalize_label(value)
    for key in CONCERN_LABELS:
        if normalized == _normalize_label(key):
            return key
    for key in CONCERN_LABELS:
        title = key.replace("_", " ")
        if normalized == _normalize_label(title):
            return key
    return fallback if fallback in CONCERN_LABELS or fallback == "unknown" else "unknown"


def _canonical_response_strategies(values: list[str], fallback: list[str] | Any) -> list[str]:
    fallback_values = [str(item) for item in fallback] if isinstance(fallback, list) else ["unknown"]
    canonical: list[str] = []
    for value in values:
        mapped = _canonical_response_strategy(value)
        if mapped is not None and mapped not in canonical:
            canonical.append(mapped)
    return canonical or fallback_values


def _canonical_response_strategy(value: str) -> str | None:
    normalized = _normalize_label(value)
    for key in RESPONSE_STRATEGY_LABELS:
        if normalized == _normalize_label(key):
            return key
    aliases = {
        "provide textual clarification": "clarify_existing_evidence",
        "textual clarification": "clarify_existing_evidence",
        "direct baseline comparison": "acknowledge_and_fix",
        "experimental validation": "add_new_experiment",
        "ablation study provision": "add_new_analysis",
        "statistical validation": "add_new_analysis",
        "data artifact submission": "acknowledge_and_fix",
    }
    return aliases.get(normalized)


def _skill_concern_type_from_id(skill_id: str) -> str:
    if not skill_id.startswith("skill_"):
        return "unknown"
    parts = skill_id[len("skill_") :].split("__", 1)
    return parts[0] if parts else "unknown"


def _normalize_label(value: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", compact)


def _alignment_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You resolve peer-review comment to author-response alignment. "
                "Return only one JSON object matching the requested schema."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "resolve_interaction_alignment",
                    "schema": {
                        "alignment_status": "matched|ambiguous|missing_response|unsupported",
                        "selected_author_unit_ids": ["string"],
                        "rationale": "string",
                        "confidence": "float 0..1",
                    },
                    "request": request,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        },
    ]


def _skill_enrichment_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You enrich peer-review skill-card semantics. "
                "Return only one JSON object matching the requested schema."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "enrich_skill_semantics",
                    "schema": {
                        "concern_type": "taxonomy label",
                        "recommended_response_strategies": ["taxonomy label"],
                        "rationale": "string",
                        "confidence": "float 0..1",
                    },
                    "request": request,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        },
    ]


def _normalize_chat_response(raw_response: dict[str, Any]) -> dict[str, Any]:
    if _looks_like_task_result(raw_response):
        return raw_response
    try:
        choices = raw_response["choices"]
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("API response did not match OpenAI chat completions shape") from exc
    if not isinstance(content, str):
        raise ValueError("API response message content is not a string")
    return extract_json_object(content)


def _urllib_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API HTTP {exc.code}: {_truncate(body)}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"API request failed: {exc.reason}") from exc
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("API response body is not a JSON object")
    return value


def _chat_completions_url(base_url: str) -> str:
    stripped = base_url.rstrip("/")
    if stripped.endswith("/v1"):
        return f"{stripped}/chat/completions"
    return f"{stripped}/v1/chat/completions"


def _is_response_format_rejection(error: str) -> bool:
    lowered = error.lower()
    return "response_format" in lowered or "json mode" in lowered


def _is_timeout_error(error: str) -> bool:
    lowered = error.lower()
    return "timed out" in lowered or "timeout" in lowered


def _read_optional_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return list(read_jsonl(path))


def _read_timeout_seconds(environment: dict[str, str] | Any) -> int:
    raw_value = str(environment.get("PEER_REVIEW_API_TIMEOUT_SECONDS", "120")).strip()
    try:
        timeout_seconds = int(raw_value)
    except ValueError as exc:
        raise ValueError("PEER_REVIEW_API_TIMEOUT_SECONDS must be an integer") from exc
    if timeout_seconds <= 0:
        raise ValueError("PEER_REVIEW_API_TIMEOUT_SECONDS must be > 0")
    return timeout_seconds


def _read_scoped_optional_jsonl(base_dir: Path, scope: str, filename: str) -> list[dict[str, Any]]:
    scoped_path = base_dir / scope / filename
    if scoped_path.exists():
        return list(read_jsonl(scoped_path))
    return _read_optional_jsonl(base_dir / filename)


def _pending_api_requests(
    requests: list[dict[str, Any]],
    completed_request_ids: set[str],
) -> tuple[list[dict[str, Any]], int]:
    pending: list[dict[str, Any]] = []
    skipped_count = 0
    for request in requests:
        if str(request.get("request_id")) in completed_request_ids:
            skipped_count += 1
            continue
        pending.append(request)
    return pending, skipped_count


def _limit_requests(
    records: Iterable[tuple[str, dict[str, Any]]],
    limit: int | None,
) -> list[tuple[str, dict[str, Any]]]:
    if limit is None:
        return list(records)
    if limit < 0:
        raise ValueError("limit must be >= 0")
    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for queue_name, record in records:
        if queue_name not in grouped:
            grouped[queue_name] = []
            order.append(queue_name)
        grouped[queue_name].append(record)

    selected: list[tuple[str, dict[str, Any]]] = []
    while len(selected) < limit and any(grouped.values()):
        for queue_name in order:
            if len(selected) >= limit:
                break
            if grouped[queue_name]:
                selected.append((queue_name, grouped[queue_name].pop(0)))
    return selected


def _merge_api_result_records(
    existing_records: list[dict[str, Any]],
    new_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []
    for record in existing_records + new_records:
        request_id = str(record.get("request_id") or "")
        if not request_id:
            continue
        if request_id not in merged:
            ordered_ids.append(request_id)
        merged[request_id] = record
    return [merged[request_id] for request_id in ordered_ids]


def _require_fields(record: dict[str, Any], required: set[str]) -> None:
    missing = sorted(field for field in required if field not in record)
    if missing:
        raise ValueError(f"model result missing required fields: {', '.join(missing)}")


def _looks_like_task_result(record: dict[str, Any]) -> bool:
    task_fields = {
        "alignment_status",
        "selected_author_unit_ids",
        "concern_type",
        "recommended_response_strategies",
    }
    return bool(task_fields.intersection(record))


def _truncate(text: str, limit: int = 500) -> str:
    return text if len(text) <= limit else text[:limit] + "..."
