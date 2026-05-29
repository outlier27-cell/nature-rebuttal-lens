"""
Manuscript context helpers for Nature RebuttalLens.

This module intentionally keeps manuscript parsing conservative. It can build
section-level context from plain text, Markdown, or LaTeX-like text. Binary PDF
or DOCX extraction should be added through explicit parsers, not guessed here.
"""

from pathlib import Path
from typing import Any


TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".tex"}


def load_manuscript_context(path: str | Path | None) -> dict[str, Any]:
    """Load manuscript context from a text-like file or return review-only mode."""
    if path is None:
        return _review_only_context()

    manuscript_path = Path(path)
    if not manuscript_path.exists():
        raise FileNotFoundError(f"manuscript file not found: {manuscript_path}")
    if manuscript_path.suffix.lower() not in TEXT_SUFFIXES:
        raise ValueError(
            "Nature RebuttalLens currently accepts text, Markdown, or LaTeX manuscript files. "
            f"Unsupported suffix: {manuscript_path.suffix}"
        )

    text = manuscript_path.read_text(encoding="utf-8")
    return build_manuscript_context(text, source_path=manuscript_path)


def build_manuscript_context(
    manuscript_text: str | None,
    *,
    source_path: str | Path | None = None,
) -> dict[str, Any]:
    text = (manuscript_text or "").strip()
    if not text:
        return _review_only_context(source_path=source_path)

    sections = _split_sections(text)
    return {
        "mode": "manuscript_aware",
        "source_path": str(source_path) if source_path is not None else None,
        "section_count": len(sections),
        "sections": sections,
        "evidence_boundary": {
            "can_locate_textual_evidence": True,
            "requires_author_confirmation": True,
            "no_binary_ocr_claim": True,
            "no_unverified_experiment_claim": True,
        },
    }


def build_rebuttal_lens_unit(
    *,
    review_text: str,
    response_text: str = "",
    manuscript_path: str | Path | None = None,
    manuscript_text: str | None = None,
    editor_text: str = "",
    unit_id: str = "rebuttal_lens_user_case",
) -> dict[str, Any]:
    if manuscript_path is not None and manuscript_text is not None:
        raise ValueError("Pass either manuscript_path or manuscript_text, not both")
    manuscript_context = (
        load_manuscript_context(manuscript_path)
        if manuscript_path is not None
        else build_manuscript_context(manuscript_text)
    )
    return {
        "unit_id": unit_id,
        "review_text": review_text,
        "response_text": response_text,
        "editor_text": editor_text,
        "manuscript_context": manuscript_context,
        "provenance": {
            "input_source": "user_supplied",
            "manuscript_mode": manuscript_context.get("mode"),
            "author_confirmation_required": True,
        },
    }


def _review_only_context(source_path: str | Path | None = None) -> dict[str, Any]:
    return {
        "mode": "review_only",
        "source_path": str(source_path) if source_path is not None else None,
        "section_count": 0,
        "sections": [],
        "evidence_boundary": {
            "can_locate_textual_evidence": False,
            "requires_author_confirmation": True,
            "missing_manuscript_warning": (
                "No manuscript text was supplied; evidence recommendations must be "
                "treated as planning questions, not claims about the manuscript."
            ),
        },
    }


def _split_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current_heading = "Manuscript"
    current_lines: list[str] = []

    for line in text.splitlines():
        heading = _heading_from_line(line)
        if heading is not None:
            if current_lines or sections:
                sections.append(_section_record(len(sections) + 1, current_heading, current_lines))
            current_heading = heading
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines or not sections:
        sections.append(_section_record(len(sections) + 1, current_heading, current_lines))

    return sections


def _heading_from_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith("#"):
        return stripped.lstrip("#").strip() or "Untitled"
    lower = stripped.lower()
    if lower.startswith("\\section{") and stripped.endswith("}"):
        return stripped[len("\\section{"):-1].strip() or "Untitled"
    if lower.startswith("\\subsection{") and stripped.endswith("}"):
        return stripped[len("\\subsection{"):-1].strip() or "Untitled"
    common = {
        "abstract",
        "introduction",
        "methods",
        "materials and methods",
        "results",
        "discussion",
        "conclusion",
        "references",
    }
    if lower in common:
        return stripped
    return None


def _section_record(index: int, heading: str, lines: list[str]) -> dict[str, Any]:
    body = "\n".join(lines).strip()
    return {
        "section_id": f"section_{index:03d}",
        "heading": heading,
        "text": body,
        "char_count": len(body),
        "provenance": {
            "source": "manuscript_text",
            "section_index": index,
        },
    }
