from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = Path("scraped_data/20_curated/final_nature_science_peer_review_corpus")
RAW_INDEX_PATH = Path("scraped_data/20_curated/final_nature_science_peer_review_corpus_index.json")
LEGACY_RAW_DATA_DIR = Path("scraped_data/20_curated/final_nature_ai_comments")
LEGACY_RAW_INDEX_PATH = Path("scraped_data/20_curated/final_nature_ai_comments_index.json")
PROCESSED_DIR = Path("data/processed")
EVALUATION_DIR = Path("data/evaluation")


def resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def project_relative_path(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return candidate.as_posix()
