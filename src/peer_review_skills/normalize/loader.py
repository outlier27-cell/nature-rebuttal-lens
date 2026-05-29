from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from peer_review_skills.config import (
    EVALUATION_DIR,
    LEGACY_RAW_DATA_DIR,
    LEGACY_RAW_INDEX_PATH,
    RAW_DATA_DIR,
    RAW_INDEX_PATH,
    resolve_project_path,
)
from peer_review_skills.evaluation.diagnostics import doi_to_paper_id, load_json


@dataclass(frozen=True)
class RawPaper:
    raw_json_path: Path
    data: dict[str, Any]


def resolve_raw_dataset_path(preferred_path: str | Path, fallback_path: str | Path) -> Path:
    preferred = resolve_project_path(preferred_path)
    if preferred.exists():
        return preferred
    return resolve_project_path(fallback_path)


def load_index_records(
    raw_index_path: str | Path,
    fallback_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    if fallback_path is None:
        fallback_path = LEGACY_RAW_INDEX_PATH if Path(raw_index_path) == RAW_INDEX_PATH else raw_index_path
    records = load_json(resolve_raw_dataset_path(raw_index_path, fallback_path))
    return {
        record.get("doi"): record
        for record in records
        if isinstance(record, dict) and record.get("doi")
    }


def load_mvp_paper_ids(path: str | Path | None = None) -> set[str]:
    ids_path = resolve_project_path(path or EVALUATION_DIR / "samples" / "mvp_paper_ids.txt")
    if not ids_path.exists():
        raise FileNotFoundError(f"MVP paper ID file not found: {ids_path}")
    return {line.strip() for line in ids_path.read_text(encoding="utf-8").splitlines() if line.strip()}


def load_raw_papers(
    raw_data_dir: str | Path,
    scope: str = "all",
    fallback_dir: str | Path | None = None,
) -> Iterator[RawPaper]:
    if scope not in {"all", "mvp"}:
        raise ValueError("scope must be 'all' or 'mvp'")

    mvp_ids = load_mvp_paper_ids() if scope == "mvp" else None
    if fallback_dir is None:
        fallback_dir = LEGACY_RAW_DATA_DIR if Path(raw_data_dir) == RAW_DATA_DIR else raw_data_dir
    data_dir = resolve_raw_dataset_path(raw_data_dir, fallback_dir)
    for path in sorted(data_dir.glob("*.json")):
        data = load_json(path)
        doi = str(data.get("doi") or path.stem.replace("_", "/"))
        paper_id = doi_to_paper_id(doi)
        if mvp_ids is not None and paper_id not in mvp_ids:
            continue
        yield RawPaper(raw_json_path=path, data=data)
