import argparse
import json
import os
import sys

from peer_review_skills import config
from peer_review_skills.agents.orchestrator import run_agent_workflow, run_api_handoff_workflow
from peer_review_skills.agents.providers import ExternalAPIProvider
from peer_review_skills.align.pipeline import align_annotations
from peer_review_skills.annotate.pipeline import annotate_units
from peer_review_skills.evaluation.diagnostics import audit_dataset
from peer_review_skills.evaluation.reports import (
    build_segmentation_diagnostics,
    render_alignment_report,
    render_annotation_report,
    render_data_audit_report,
    render_judge_report,
    render_segmentation_report,
    render_skill_quality_report,
    write_text,
)
from peer_review_skills.execution.build_naturereview_v01 import (
    apply_naturereview_seed_api_results,
    main as build_naturereview_v01,
    run_naturereview_seed_api_review,
    validate_and_write_report as validate_naturereview_v01,
)
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl
from peer_review_skills.indexing.review_unit_index import build_review_unit_index, load_review_unit_index
from peer_review_skills.judge.pipeline import judge_artifacts
from peer_review_skills.normalize.loader import (
    load_index_records,
    load_raw_papers,
    resolve_raw_dataset_path,
)
from peer_review_skills.normalize.paper_normalizer import normalize_papers
from peer_review_skills.sample.mvp_selector import (
    render_mvp_ids,
    render_review_samples,
    select_mvp_papers,
)
from peer_review_skills.segment.unit_builder import build_review_units_for_paper
from peer_review_skills.skills.pipeline import induce_skill_cards, write_skill_card_files
from peer_review_skills.taxonomy.pipeline import build_taxonomy_artifacts


def _require_rebuttal_lens_api_config(parser: argparse.ArgumentParser) -> dict[str, str]:
    """Read API config for the public CLI and report missing keys without traceback."""
    api_base = os.environ.get("PEER_REVIEW_API_BASE_URL", "https://xh.v1api.cc").strip()
    api_key = os.environ.get("PEER_REVIEW_API_KEY", "").strip()
    model = os.environ.get("PEER_REVIEW_API_MODEL", "deepseek-v3").strip()
    missing = []
    if not api_base:
        missing.append("PEER_REVIEW_API_BASE_URL")
    if not api_key:
        missing.append("PEER_REVIEW_API_KEY")
    if not model:
        missing.append("PEER_REVIEW_API_MODEL")
    if missing:
        parser.error(
            "missing "
            + ", ".join(missing)
            + "; set PEER_REVIEW_API_BASE_URL, PEER_REVIEW_API_KEY, and PEER_REVIEW_API_MODEL "
            "before running Nature RebuttalLens"
        )
    return {"api_base": api_base, "api_key": api_key, "model": model}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="peer-review-skills",
        description="Nature peer review skill discovery pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("audit", help="Run data audit and write report")

    select_mvp = subparsers.add_parser(
        "select-mvp", help="Select MVP paper IDs and segmentation review samples"
    )
    select_mvp.add_argument("--n", type=int, default=100)
    select_mvp.add_argument("--review-samples", type=int, default=30)

    normalize = subparsers.add_parser("normalize", help="Normalize raw paper JSON")
    normalize.add_argument("--scope", choices=("mvp", "all"), default="mvp")

    segment = subparsers.add_parser("segment", help="Segment normalized papers")
    segment.add_argument("--scope", choices=("mvp", "all"), default="mvp")

    annotate = subparsers.add_parser("annotate", help="Annotate reviewer and author units")
    annotate.add_argument("--scope", choices=("mvp", "all"), default="mvp")

    align = subparsers.add_parser("align", help="Align reviewer concerns to author responses")
    align.add_argument("--scope", choices=("mvp", "all"), default="mvp")

    subparsers.add_parser("write-taxonomies", help="Write versioned taxonomy artifacts")

    induce = subparsers.add_parser("induce-skills", help="Induce grounded skill cards")
    induce.add_argument("--scope", choices=("mvp", "all"), default="mvp")

    judge = subparsers.add_parser("judge", help="Run local QA judge over generated artifacts")
    judge.add_argument("--scope", choices=("mvp", "all"), default="mvp")

    run_agents = subparsers.add_parser("run-agents", help="Run local multi-agent pipeline wrapper")
    run_agents.add_argument("--scope", choices=("mvp", "all"), default="mvp")
    run_agents.add_argument("--provider", choices=("external-api",), default="external-api")
    run_agents.add_argument("--skip-normalize", action="store_true")
    run_agents.add_argument("--skip-segment", action="store_true")
    run_agents.add_argument("--skip-annotate", action="store_true")
    run_agents.add_argument("--enforce-quality-gate", action="store_true")
    run_agents.add_argument("--execute-api", action="store_true")
    run_agents.add_argument("--api-limit", type=int, default=5)

    run_api = subparsers.add_parser("run-api", help="Run queued OpenAI-compatible API handoff requests")
    run_api.add_argument("--scope", choices=("mvp", "all"), default="mvp")
    run_api.add_argument("--limit", type=int, default=5)
    run_api.add_argument("--apply-results", action="store_true")

    subparsers.add_parser(
        "build-naturereview-v01",
        help="Build non-API NatureReview-Interact v0.1 artifacts from existing v2709 data",
    )
    subparsers.add_parser(
        "validate-naturereview-v01",
        help="Validate NatureReview-Interact v0.1 artifacts and write validation report",
    )
    run_seed_api = subparsers.add_parser(
        "run-naturereview-seed-api-review",
        help="Run OpenAI-compatible API review for NatureReview-Interact v0.1 seed requests",
    )
    run_seed_api.add_argument("--limit", type=int, default=None)
    run_seed_api.add_argument("--sleep-seconds", type=float, default=0.0)
    subparsers.add_parser(
        "apply-naturereview-seed-api-results",
        help="Apply NatureReview-Interact v0.1 seed API review results and rebuild derived artifacts",
    )
    run_naturereview_multi_agent = subparsers.add_parser(
        "run-naturereview-multi-agent",
        help="Run the true multi-agent NatureReview-Interact workflow over the v0.1 KB",
    )
    run_naturereview_multi_agent.add_argument("--limit", type=int, default=5)
    run_naturereview_multi_agent.add_argument("--enable-refinement", action="store_true")
    run_naturereview_multi_agent.add_argument("--max-refinement-iterations", type=int, default=2)
    run_rebuttal_lens = subparsers.add_parser(
        "run-rebuttal-lens",
        aliases=["run-reviewweaver"],
        help="Run Nature RebuttalLens manuscript-aware author rebuttal assistant workflow",
    )
    run_rebuttal_lens.add_argument("--review-file", type=config.Path, required=True)
    run_rebuttal_lens.add_argument("--manuscript-file", type=config.Path, default=None)
    run_rebuttal_lens.add_argument("--response-file", type=config.Path, default=None)
    run_rebuttal_lens.add_argument("--editor-file", type=config.Path, default=None)
    run_rebuttal_lens.add_argument("--retrieved-cases-file", type=config.Path, default=None)
    run_rebuttal_lens.add_argument("--output-dir", type=config.Path, default=None)
    run_rebuttal_lens.add_argument("--limit-cases", type=int, default=5)
    run_rebuttal_lens.add_argument(
        "--reset-memory",
        action="store_true",
        help="Declare this run independent from any cross-run strategy or author-preference memory.",
    )
    run_rebuttal_lens.add_argument(
        "--workflow-engine",
        choices=("layered", "dag"),
        default=None,
    )
    run_rebuttal_lens.add_argument(
        "--enable-committee",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    run_rebuttal_lens.add_argument(
        "--enable-strategy-tournament",
        action=argparse.BooleanOptionalAction,
        default=None,
    )

    return parser


def build_rebuttal_lens_argv(argv: list[str] | None = None) -> list[str]:
    """Build argv for the installed `run-rebuttal-lens` console script."""
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] in {"run-rebuttal-lens", "run-reviewweaver"}:
        return raw_argv
    return ["run-rebuttal-lens", *raw_argv]


def run_rebuttal_lens_cli(argv: list[str] | None = None) -> int:
    """Console-script entry point for running only the Nature RebuttalLens workflow."""
    return main(build_rebuttal_lens_argv(argv))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "audit":
        effective_raw_data_dir = resolve_raw_dataset_path(
            config.RAW_DATA_DIR,
            config.LEGACY_RAW_DATA_DIR,
        )
        effective_raw_index_path = resolve_raw_dataset_path(
            config.RAW_INDEX_PATH,
            config.LEGACY_RAW_INDEX_PATH,
        )
        audit = audit_dataset(effective_raw_data_dir, effective_raw_index_path)
        report_path = config.resolve_project_path(
            config.EVALUATION_DIR / "reports" / "data_audit_report.md"
        )
        write_text(report_path, render_data_audit_report(audit))
        print(f"Effective raw data dir: {config.project_relative_path(effective_raw_data_dir)}")
        print(f"Effective raw index path: {config.project_relative_path(effective_raw_index_path)}")
        print(f"Wrote {report_path}")
        return 0
    if args.command == "select-mvp":
        audit = audit_dataset(config.RAW_DATA_DIR, config.RAW_INDEX_PATH)
        selection = select_mvp_papers(
            config.RAW_DATA_DIR,
            config.RAW_INDEX_PATH,
            audit,
            n=args.n,
            review_samples=args.review_samples,
        )
        sample_dir = config.resolve_project_path(config.EVALUATION_DIR / "samples")
        mvp_path = sample_dir / "mvp_paper_ids.txt"
        sample_path = sample_dir / "segmentation_review_sample.jsonl"
        write_text(mvp_path, render_mvp_ids(selection["mvp_paper_ids"]))
        write_text(
            sample_path,
            render_review_samples(selection["segmentation_review_samples"]),
        )
        print(f"Wrote {mvp_path}")
        print(f"Wrote {sample_path}")
        return 0
    if args.command == "normalize":
        records = normalize_papers(
            load_raw_papers(config.RAW_DATA_DIR, scope=args.scope),
            load_index_records(config.RAW_INDEX_PATH),
        )
        output_path = config.resolve_project_path(
            config.PROCESSED_DIR / "normalized" / "normalized_papers.jsonl"
        )
        write_jsonl(output_path, (record.to_dict() for record in records))
        print(f"Wrote {output_path}")
        return 0
    if args.command == "segment":
        units = []
        for raw_paper in load_raw_papers(config.RAW_DATA_DIR, scope=args.scope):
            units.extend(
                build_review_units_for_paper(
                    None,
                    str(raw_paper.raw_json_path.as_posix()),
                    raw_paper.data,
                )
            )
        output_path = config.resolve_project_path(
            config.PROCESSED_DIR / "review_units" / "review_units.jsonl"
        )
        unit_dicts = [unit.to_dict() for unit in units]
        write_jsonl(output_path, unit_dicts)
        unit_index_path = config.resolve_project_path(
            config.PROCESSED_DIR / "review_units" / "review_unit_index.jsonl"
        )
        write_jsonl(
            unit_index_path,
            build_review_unit_index(unit_dicts),
        )
        diagnostics = build_segmentation_diagnostics(unit_dicts)
        queue_path = config.resolve_project_path(
            config.EVALUATION_DIR / "review_queue" / "mixed_or_low_confidence_units.jsonl"
        )
        report_path = config.resolve_project_path(
            config.EVALUATION_DIR / "reports" / "segmentation_report.md"
        )
        write_jsonl(queue_path, diagnostics["review_queue_units"])
        write_text(report_path, render_segmentation_report(diagnostics))
        print(f"Wrote {output_path}")
        print(f"Wrote {unit_index_path}")
        print(f"Wrote {queue_path}")
        print(f"Wrote {report_path}")
        return 0
    if args.command == "annotate":
        review_units_path = config.resolve_project_path(
            config.PROCESSED_DIR / "review_units" / "review_units.jsonl"
        )
        units = list(read_jsonl(review_units_path))
        if args.scope == "mvp":
            mvp_ids = {
                line.strip()
                for line in config.resolve_project_path(
                    config.EVALUATION_DIR / "samples" / "mvp_paper_ids.txt"
                ).read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            units = [unit for unit in units if unit.get("paper_id") in mvp_ids]
        result = annotate_units(units)
        annotations_dir = config.resolve_project_path(config.PROCESSED_DIR / "annotations")
        reviewer_path = annotations_dir / "reviewer_annotations.jsonl"
        author_path = annotations_dir / "author_annotations.jsonl"
        low_confidence_path = config.resolve_project_path(
            config.EVALUATION_DIR / "review_queue" / "annotation_low_confidence_units.jsonl"
        )
        report_path = config.resolve_project_path(
            config.EVALUATION_DIR / "reports" / "annotation_report.md"
        )
        write_jsonl(
            reviewer_path,
            (annotation.to_dict() for annotation in result["reviewer_annotations"]),
        )
        write_jsonl(
            author_path,
            (annotation.to_dict() for annotation in result["author_annotations"]),
        )
        write_jsonl(low_confidence_path, result["low_confidence_annotations"])
        write_text(report_path, render_annotation_report(result["summary"]))
        print(f"Wrote {reviewer_path}")
        print(f"Wrote {author_path}")
        print(f"Wrote {low_confidence_path}")
        print(f"Wrote {report_path}")
        return 0
    if args.command == "align":
        reviewer_annotations_path = config.resolve_project_path(
            config.PROCESSED_DIR / "annotations" / "reviewer_annotations.jsonl"
        )
        author_annotations_path = config.resolve_project_path(
            config.PROCESSED_DIR / "annotations" / "author_annotations.jsonl"
        )
        reviewer_annotations = list(read_jsonl(reviewer_annotations_path))
        author_annotations = list(read_jsonl(author_annotations_path))
        unit_index_path = config.resolve_project_path(
            config.PROCESSED_DIR / "review_units" / "review_unit_index.jsonl"
        )
        unit_index = load_review_unit_index(unit_index_path) if unit_index_path.exists() else None
        if args.scope == "mvp":
            mvp_ids = {
                line.strip()
                for line in config.resolve_project_path(
                    config.EVALUATION_DIR / "samples" / "mvp_paper_ids.txt"
                ).read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            reviewer_annotations = [
                annotation for annotation in reviewer_annotations if annotation.get("paper_id") in mvp_ids
            ]
            author_annotations = [
                annotation for annotation in author_annotations if annotation.get("paper_id") in mvp_ids
            ]
        result = align_annotations(reviewer_annotations, author_annotations, unit_index=unit_index)
        interaction_path = config.resolve_project_path(
            config.PROCESSED_DIR / "interaction_units" / "interaction_units.jsonl"
        )
        unresolved_path = config.resolve_project_path(
            config.EVALUATION_DIR / "review_queue" / "unresolved_alignment_units.jsonl"
        )
        report_path = config.resolve_project_path(
            config.EVALUATION_DIR / "reports" / "alignment_report.md"
        )
        write_jsonl(
            interaction_path,
            (interaction.to_dict() for interaction in result["interaction_units"]),
        )
        write_jsonl(unresolved_path, result["unresolved_alignment_units"])
        write_text(report_path, render_alignment_report(result["summary"]))
        print(f"Wrote {interaction_path}")
        print(f"Wrote {unresolved_path}")
        print(f"Wrote {report_path}")
        return 0
    if args.command == "write-taxonomies":
        taxonomy_dir = config.resolve_project_path(config.PROCESSED_DIR / "taxonomies")
        taxonomy_dir.mkdir(parents=True, exist_ok=True)
        for filename, payload in build_taxonomy_artifacts().items():
            path = taxonomy_dir / filename
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            print(f"Wrote {path}")
        return 0
    if args.command == "induce-skills":
        interaction_path = config.resolve_project_path(
            config.PROCESSED_DIR / "interaction_units" / "interaction_units.jsonl"
        )
        interactions = list(read_jsonl(interaction_path))
        if args.scope == "mvp":
            mvp_ids = {
                line.strip()
                for line in config.resolve_project_path(
                    config.EVALUATION_DIR / "samples" / "mvp_paper_ids.txt"
                ).read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            interactions = [
                interaction for interaction in interactions if interaction.get("paper_id") in mvp_ids
            ]
        result = induce_skill_cards(interactions)
        skill_dir = write_skill_card_files(config.PROJECT_ROOT, args.scope, result["skill_cards"])
        report_path = config.resolve_project_path(
            config.EVALUATION_DIR / "reports" / "skill_quality_report.md"
        )
        write_text(report_path, render_skill_quality_report(result["summary"]))
        print(f"Wrote {skill_dir}")
        print(f"Wrote {report_path}")
        return 0
    if args.command == "judge":
        result = judge_artifacts(config.PROJECT_ROOT, scope=args.scope)
        qa_dir = config.resolve_project_path(config.EVALUATION_DIR / "qa")
        accepted_interactions_path = qa_dir / "accepted_interactions.jsonl"
        rejected_interactions_path = qa_dir / "rejected_interactions.jsonl"
        accepted_skill_cards_path = qa_dir / "accepted_skill_cards.jsonl"
        rejected_skill_cards_path = qa_dir / "rejected_skill_cards.jsonl"
        skill_cards_for_review_path = qa_dir / "skill_cards_for_review.jsonl"
        issues_path = qa_dir / "judge_issues.jsonl"
        report_path = config.resolve_project_path(
            config.EVALUATION_DIR / "reports" / "judge_report.md"
        )
        write_jsonl(accepted_interactions_path, result["accepted_interactions"])
        write_jsonl(rejected_interactions_path, result["rejected_interactions"])
        write_jsonl(accepted_skill_cards_path, result["accepted_skill_cards"])
        write_jsonl(rejected_skill_cards_path, result["rejected_skill_cards"])
        write_jsonl(skill_cards_for_review_path, result["skill_cards_for_review"])
        write_jsonl(issues_path, result["errors"] + result["warnings"])
        write_text(report_path, render_judge_report(result))
        print(f"Wrote {accepted_interactions_path}")
        print(f"Wrote {rejected_interactions_path}")
        print(f"Wrote {accepted_skill_cards_path}")
        print(f"Wrote {rejected_skill_cards_path}")
        print(f"Wrote {skill_cards_for_review_path}")
        print(f"Wrote {issues_path}")
        print(f"Wrote {report_path}")
        return 0
    if args.command == "run-agents":
        provider = ExternalAPIProvider.from_environment()
        result = run_agent_workflow(
            config.PROJECT_ROOT,
            scope=args.scope,
            provider=provider,
            skip_normalize=args.skip_normalize,
            skip_segment=args.skip_segment,
            skip_annotate=args.skip_annotate,
            enforce_quality_gate=args.enforce_quality_gate,
            execute_api=args.execute_api,
            api_limit=args.api_limit,
        )
        report_path = config.resolve_project_path(
            config.EVALUATION_DIR / "reports" / "agent_workflow_report.md"
        )
        print(f"Wrote {report_path}")
        print(
            "Agent workflow summary: "
            f"{result['outputs'].get('interaction_count', 0)} interactions, "
            f"{result['outputs'].get('skill_card_count', 0)} skill cards, "
            f"{result['outputs'].get('judge_error_count', 0)} judge errors"
        )
        return 0
    if args.command == "run-api":
        result = run_api_handoff_workflow(
            config.PROJECT_ROOT,
            limit=args.limit,
            apply_results=args.apply_results,
            scope=args.scope,
        )
        report_path = config.resolve_project_path(
            config.EVALUATION_DIR / "reports" / "api_execution_report.md"
        )
        print(f"Wrote {report_path}")
        print(
            "API execution summary: "
            f"{result['outputs'].get('api_processed_request_count', 0)} processed, "
            f"{result['outputs'].get('api_error_count', 0)} errors"
        )
        return 0
    if args.command == "build-naturereview-v01":
        build_naturereview_v01()
        print("Built NatureReview-Interact v0.1 non-API artifacts")
        return 0
    if args.command == "validate-naturereview-v01":
        validation = validate_naturereview_v01()
        print(f"NatureReview-Interact v0.1 validation: {validation['overall_status']}")
        print(json.dumps(validation["counts"], ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "run-naturereview-seed-api-review":
        base_url = (
            os.environ.get("OPENAI_COMPATIBLE_BASE_URL")
            or os.environ.get("PEER_REVIEW_API_BASE_URL")
            or "https://xh.v1api.cc"
        )
        api_key = os.environ.get("OPENAI_COMPATIBLE_API_KEY") or os.environ.get("PEER_REVIEW_API_KEY") or ""
        model = os.environ.get("OPENAI_COMPATIBLE_MODEL") or os.environ.get("PEER_REVIEW_API_MODEL") or "deepseek-v3"
        if not api_key.strip():
            parser.error("missing OPENAI_COMPATIBLE_API_KEY or PEER_REVIEW_API_KEY")
        summary = run_naturereview_seed_api_review(
            base_url=base_url,
            api_key=api_key,
            model=model,
            limit=args.limit,
            sleep_seconds=args.sleep_seconds,
        )
        print("NatureReview seed API review summary:")
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "apply-naturereview-seed-api-results":
        summary = apply_naturereview_seed_api_results()
        print("Applied NatureReview seed API results:")
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "run-naturereview-multi-agent":
        from peer_review_skills.agents.workflow_integration import run_multi_agent_workflow

        summary = run_multi_agent_workflow(
            config.PROJECT_ROOT,
            scope="mvp",
            config={
                "limit": args.limit,
                "enable_refinement": args.enable_refinement,
                "max_refinement_iterations": args.max_refinement_iterations,
            },
        )
        print("NatureReview true multi-agent workflow summary:")
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command in {"run-rebuttal-lens", "run-reviewweaver"}:
        from peer_review_skills.agents.rebuttal_lens_workflow import run_rebuttal_lens_workflow

        review_text = config.resolve_project_path(args.review_file).read_text(encoding="utf-8")
        response_text = (
            config.resolve_project_path(args.response_file).read_text(encoding="utf-8")
            if args.response_file is not None
            else ""
        )
        editor_text = (
            config.resolve_project_path(args.editor_file).read_text(encoding="utf-8")
            if args.editor_file is not None
            else ""
        )
        workflow_config = {
            "enable_refinement": False,
            "max_refinement_iterations": 0,
            **_require_rebuttal_lens_api_config(parser),
        }
        if args.workflow_engine is not None:
            workflow_config["workflow_engine"] = args.workflow_engine
        if args.enable_committee is not None:
            workflow_config["enable_committee"] = args.enable_committee
        if args.enable_strategy_tournament is not None:
            workflow_config["enable_strategy_tournament"] = args.enable_strategy_tournament
        if args.reset_memory:
            workflow_config["reset_memory"] = True
        if args.output_dir is not None:
            workflow_config["output_dir"] = config.resolve_project_path(args.output_dir)
        retrieved_cases = []
        if args.retrieved_cases_file is not None:
            retrieved_case_payload = json.loads(
                config.resolve_project_path(args.retrieved_cases_file).read_text(encoding="utf-8")
            )
            if isinstance(retrieved_case_payload, dict):
                retrieved_cases = list(retrieved_case_payload.get("top_k", []))[: args.limit_cases]
            elif isinstance(retrieved_case_payload, list):
                retrieved_cases = list(retrieved_case_payload)[: args.limit_cases]
            else:
                parser.error("--retrieved-cases-file must contain a JSON object or array")
        summary = run_rebuttal_lens_workflow(
            project_root=config.PROJECT_ROOT,
            review_text=review_text,
            response_text=response_text,
            manuscript_path=(
                config.resolve_project_path(args.manuscript_file)
                if args.manuscript_file is not None
                else None
            ),
            editor_text=editor_text,
            retrieved_cases=retrieved_cases,
            config=workflow_config,
        )
        print("Nature RebuttalLens workflow summary:")
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    parser.error(f"command not implemented yet: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
