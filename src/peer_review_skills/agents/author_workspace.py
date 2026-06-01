"""Static author workspace renderer for RebuttalLens reports."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def write_author_workspace_html(report: dict[str, Any], output_dir: str | Path) -> Path:
    """Write a single-file, script-free author action workspace."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / "author_workspace.html"
    path.write_text(render_author_workspace_html(report), encoding="utf-8", newline="\n")
    return path


def render_author_workspace_html(report: dict[str, Any]) -> str:
    """Render an HTML planning workspace, not final rebuttal text."""
    cards = _cards(report)
    return "\n".join([
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        "  <title>Nature RebuttalLens Author Workspace</title>",
        "  <style>",
        _css(),
        "  </style>",
        "</head>",
        "<body>",
        '  <main class="workspace">',
        '    <header class="topbar">',
        "      <div>",
        "        <h1>Nature RebuttalLens Author Workspace</h1>",
        f"        <p>{escape(str(report.get('executive_summary') or 'Evidence-first response planning workspace.'))}</p>",
        "      </div>",
        '      <strong class="boundary">not final submission text</strong>',
        "    </header>",
        '    <section class="grid" aria-label="Reviewer concern action workspace">',
        *cards,
        "    </section>",
        "  </main>",
        "</body>",
        "</html>",
        "",
    ])


def _cards(report: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for card in report.get("comment_cards", []):
        if not isinstance(card, dict):
            continue
        status = _status_for(card)
        lines.extend([
            '      <article class="card">',
            "        <div>",
            f"          <span class=\"status {escape(status.replace(' ', '-'))}\">{escape(status)}</span>",
            f"          <h2>{escape(str(card.get('comment_id') or 'comment'))}: {escape(str(card.get('concern_type') or 'unknown'))}</h2>",
            "        </div>",
            f"        <p class=\"surface\">{escape(str(card.get('surface_request') or ''))}</p>",
            "        <dl>",
            f"          <dt>Evidence</dt><dd>{escape(str(card.get('evidence_status') or 'uncertain'))}</dd>",
            f"          <dt>Gap</dt><dd>{escape(str(card.get('evidence_gap') or ''))}</dd>",
            f"          <dt>Action</dt><dd>{escape(str(card.get('recommended_action') or ''))}</dd>",
            f"          <dt>Ledger</dt><dd>{escape(str(card.get('ledger_id') or 'unlinked'))}</dd>",
            "        </dl>",
            f"        <p><b>Safe:</b> {escape(str(card.get('safe_response_language') or ''))}</p>",
            f"        <p><b>Avoid:</b> {escape(str(card.get('unsafe_language_to_avoid') or ''))}</p>",
            "      </article>",
        ])
    if not lines:
        lines.append('      <p class="empty">No comment cards available.</p>')
    return lines


def _status_for(card: dict[str, Any]) -> str:
    evidence_status = str(card.get("evidence_status") or "").strip()
    if evidence_status in {"missing", "uncertain", ""}:
        return "needs evidence"
    if bool(card.get("author_input_required")):
        return "needs author confirmation"
    return "ready to draft"


def _css() -> str:
    return """
    :root {
      color: #17202a;
      background: #f6f7f9;
      font-family: Arial, Helvetica, sans-serif;
    }
    body { margin: 0; }
    .workspace { max-width: 1180px; margin: 0 auto; padding: 24px; }
    .topbar {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      border-bottom: 1px solid #d8dde6;
      padding-bottom: 16px;
    }
    h1 { font-size: 28px; margin: 0 0 8px; }
    h2 { font-size: 18px; margin: 12px 0; }
    p { line-height: 1.5; }
    .boundary, .status {
      border: 1px solid #8b98aa;
      border-radius: 4px;
      padding: 6px 8px;
      background: #ffffff;
      white-space: nowrap;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      margin-top: 20px;
    }
    .card {
      background: #ffffff;
      border: 1px solid #d8dde6;
      border-radius: 8px;
      padding: 16px;
    }
    .status.needs-evidence { border-color: #b42318; color: #b42318; }
    .status.needs-author-confirmation { border-color: #946200; color: #7a4f00; }
    .status.ready-to-draft { border-color: #087443; color: #087443; }
    dl { display: grid; grid-template-columns: 92px 1fr; gap: 6px 10px; }
    dt { font-weight: 700; }
    dd { margin: 0; }
    .surface { font-weight: 700; }
    .empty { padding: 20px; background: #ffffff; border: 1px solid #d8dde6; }
    @media (max-width: 640px) {
      .workspace { padding: 16px; }
      .topbar { display: block; }
      .boundary { display: inline-block; margin-top: 8px; }
      .grid { grid-template-columns: 1fr; }
    }
    """.strip()
