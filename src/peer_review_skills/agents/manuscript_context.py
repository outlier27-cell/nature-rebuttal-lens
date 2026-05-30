"""
Manuscript context helpers for Nature RebuttalLens.

This module intentionally keeps manuscript parsing conservative. It can build
section-level context from plain text, Markdown, LaTeX-like text, extractable
PDF text, and Word documents. It does not perform OCR or claim image/table
understanding.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from zipfile import ZipFile
import xml.etree.ElementTree as ET


TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".tex"}
PDF_SUFFIXES = {".pdf"}
DOCX_SUFFIXES = {".docx", ".docm"}
LEGACY_DOC_SUFFIXES = {".doc"}


def load_manuscript_context(path: str | Path | None) -> dict[str, Any]:
    """Load manuscript context from a supported file or return review-only mode."""
    if path is None:
        return _review_only_context()

    manuscript_path = Path(path)
    if not manuscript_path.exists():
        raise FileNotFoundError(f"manuscript file not found: {manuscript_path}")

    suffix = manuscript_path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        text = manuscript_path.read_text(encoding="utf-8")
        return build_manuscript_context(
            text,
            source_path=manuscript_path,
            extraction=_extraction_record("text"),
        )
    if suffix in PDF_SUFFIXES:
        return build_manuscript_context(
            _extract_pdf_text(manuscript_path),
            source_path=manuscript_path,
            extraction=_extraction_record("pdf"),
        )
    if suffix in DOCX_SUFFIXES:
        return build_manuscript_context(
            _extract_docx_text(manuscript_path),
            source_path=manuscript_path,
            extraction=_extraction_record("docx"),
        )
    if suffix in LEGACY_DOC_SUFFIXES:
        return build_manuscript_context(
            _extract_legacy_doc_text(manuscript_path),
            source_path=manuscript_path,
            extraction=_extraction_record("doc"),
        )
    raise ValueError(
        "Nature RebuttalLens accepts text, Markdown, LaTeX, PDF, DOCX, or DOC manuscript files. "
        f"Unsupported suffix: {manuscript_path.suffix}"
    )


def build_manuscript_context(
    manuscript_text: str | None,
    *,
    source_path: str | Path | None = None,
    extraction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = (manuscript_text or "").strip()
    if not text:
        return _review_only_context(source_path=source_path, extraction=extraction)

    sections = _split_sections(text)
    context = {
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
    if extraction is not None:
        context["extraction"] = extraction
    return context


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


def _review_only_context(
    source_path: str | Path | None = None,
    extraction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = {
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
    if extraction is not None:
        context["extraction"] = extraction
    return context


def _extraction_record(file_format: str) -> dict[str, Any]:
    return {
        "format": file_format,
        "method": {
            "text": "utf8_text",
            "pdf": "pdfplumber_extract_text",
            "docx": "docx_xml_text",
            "doc": "soffice_to_docx_then_docx_xml_text",
        }[file_format],
        "ocr_performed": False,
        "image_or_table_understanding": False,
    }


def _extract_pdf_text(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "PDF manuscript parsing requires pdfplumber. Install it with "
            "`python -m pip install pdfplumber` and retry."
        ) from exc

    page_texts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                page_texts.append(f"Page {page_index}\n{text.strip()}")
    return "\n\n".join(page_texts)


def _extract_docx_text(path: Path) -> str:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    with ZipFile(path) as archive:
        try:
            document_xml = archive.read("word/document.xml")
        except KeyError as exc:
            raise ValueError(f"DOCX file does not contain word/document.xml: {path}") from exc
    root = ET.fromstring(document_xml)
    for paragraph in root.findall(".//w:p", namespace):
        fragments = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        text = "".join(fragments).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_legacy_doc_text(path: Path) -> str:
    converter = shutil.which("soffice") or shutil.which("libreoffice")
    if converter is None:
        raise RuntimeError(
            "LibreOffice/soffice is required to parse legacy .doc manuscripts. "
            "Convert the file to .docx manually or install LibreOffice and retry."
        )
    with tempfile.TemporaryDirectory(prefix="rebuttal_lens_doc_") as tmp_dir:
        output_dir = Path(tmp_dir)
        command = [
            converter,
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(output_dir),
            str(path),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
        converted_path = output_dir / f"{path.stem}.docx"
        if result.returncode != 0 or not converted_path.exists():
            stderr = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                "Failed to convert legacy .doc manuscript to .docx with LibreOffice/soffice"
                + (f": {stderr}" if stderr else "")
            )
        return _extract_docx_text(converted_path)


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
