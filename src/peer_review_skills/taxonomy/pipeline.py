from typing import Any


TAXONOMY_VERSION = "v1"


CONCERN_LABELS = {
    "baseline_comparison": {
        "definition": "Reviewer asks whether the work is compared against appropriate prior methods, baselines, or state-of-the-art alternatives.",
        "examples": ["Please compare the proposed model with stronger baseline methods."],
        "evidence_cues": ["baseline", "comparison", "state-of-the-art", "SOTA"],
    },
    "generalization_scope": {
        "definition": "Reviewer questions whether claims hold outside the reported setting, dataset, population, domain, or validation context.",
        "examples": ["The method should be tested on an external dataset."],
        "evidence_cues": ["generalize", "external validation", "other dataset", "robustness"],
    },
    "reproducibility_reporting": {
        "definition": "Reviewer requests clearer data, code, parameter, protocol, or availability information needed to reproduce the work.",
        "examples": ["Please release the code and training data used for the model."],
        "evidence_cues": ["code", "data availability", "reproduce", "GitHub", "Zenodo"],
    },
    "statistics_significance": {
        "definition": "Reviewer challenges statistical testing, uncertainty, sample size, significance, or quantitative confidence.",
        "examples": ["Report confidence intervals and statistical significance for the results."],
        "evidence_cues": ["p-value", "confidence interval", "sample size", "significance"],
    },
    "ablation_mechanism": {
        "definition": "Reviewer asks for ablations, mechanism analysis, feature contribution, or explanation of why the method works.",
        "examples": ["An ablation study is needed to show which component drives the gain."],
        "evidence_cues": ["ablation", "mechanism", "feature importance", "SHAP"],
    },
    "clarity_presentation": {
        "definition": "Reviewer requests clearer wording, figures, legends, organization, or editorial presentation.",
        "examples": ["Figure labels are difficult to read and should be clarified."],
        "evidence_cues": ["clarify", "unclear", "figure", "legend", "typo"],
    },
    "experimental_design": {
        "definition": "Reviewer questions whether the experiments, controls, validations, or study design are sufficient for the claim.",
        "examples": ["A prospective validation experiment would strengthen the study."],
        "evidence_cues": ["experiment", "validation", "control", "prospective"],
    },
    "dataset_bias_ethics_safety": {
        "definition": "Reviewer raises bias, fairness, privacy, ethics, safety, or dataset representativeness concerns.",
        "examples": ["The authors should discuss potential bias in the training data."],
        "evidence_cues": ["bias", "ethics", "privacy", "fairness", "safety"],
    },
    "theoretical_validity": {
        "definition": "Reviewer challenges assumptions, formal validity, causality, or theoretical justification.",
        "examples": ["The causal assumptions behind the model require more justification."],
        "evidence_cues": ["assumption", "causal", "theoretical", "validity"],
    },
    "novelty_positioning": {
        "definition": "Reviewer questions originality, contribution, or positioning against related work.",
        "examples": ["The novelty over prior work is not sufficiently clear."],
        "evidence_cues": ["novelty", "incremental", "contribution", "related work"],
    },
}


RESPONSE_STRATEGY_LABELS = {
    "acknowledge_and_fix": {
        "definition": "Author accepts the point and reports a concrete manuscript, analysis, data, figure, or wording change.",
        "examples": ["We agree and have revised the manuscript to include the requested comparison."],
        "evidence_cues": ["we agree", "we revised", "we added", "we corrected"],
    },
    "clarify_existing_evidence": {
        "definition": "Author explains evidence already present or clarifies interpretation without adding substantial new work.",
        "examples": ["We clarify that the validation cohort was independent."],
        "evidence_cues": ["to clarify", "we explain", "we have clarified"],
    },
    "add_new_experiment": {
        "definition": "Author adds or reports a new experiment, validation, control, or empirical study in response.",
        "examples": ["We conducted an additional validation experiment."],
        "evidence_cues": ["new experiment", "we performed", "we conducted"],
    },
    "add_new_analysis": {
        "definition": "Author adds a new computational, statistical, robustness, ablation, or re-analysis.",
        "examples": ["We added a new ablation analysis in Supplementary Figure 4."],
        "evidence_cues": ["additional analysis", "new analysis", "ablation"],
    },
    "narrow_claim_scope": {
        "definition": "Author limits, softens, or removes a claim to match the available evidence.",
        "examples": ["We toned down the claim and now restrict it to the tested dataset."],
        "evidence_cues": ["toned down", "narrowed", "removed the claim"],
    },
    "contest_reviewer_premise": {
        "definition": "Author respectfully disagrees with the reviewer premise or argues the requested change is not applicable.",
        "examples": ["We respectfully disagree because the suggested baseline solves a different task."],
        "evidence_cues": ["we disagree", "respectfully disagree", "not applicable"],
    },
    "defer_future_work": {
        "definition": "Author acknowledges the limitation but places the requested work outside the current study scope.",
        "examples": ["We agree this is important and now discuss it as future work."],
        "evidence_cues": ["future work", "beyond the scope", "future studies"],
    },
    "justify_method_choice": {
        "definition": "Author defends a design, dataset, metric, model, or protocol choice with rationale.",
        "examples": ["We chose this metric because it is standard for the benchmark."],
        "evidence_cues": ["we chose", "because", "rationale", "we used"],
    },
    "reframe_contribution": {
        "definition": "Author shifts the framing of the contribution or emphasizes a different value proposition.",
        "examples": ["We now emphasize the method as a screening tool rather than a final predictor."],
        "evidence_cues": ["we emphasize", "reframed", "highlight"],
    },
    "editorial_only_change": {
        "definition": "Author responds with copyediting, formatting, figure legend, typo, or minor presentation updates.",
        "examples": ["We corrected the typo and improved the figure legend."],
        "evidence_cues": ["typo", "grammar", "format", "legend"],
    },
}


SKILL_LABELS = {
    "evidence_upgrade": {
        "definition": "Turn a reviewer evidence request into a concrete new experiment, analysis, baseline, or reproducibility artifact.",
        "examples": ["Add a missing baseline, ablation, validation cohort, or code/data artifact."],
        "evidence_cues": ["baseline", "experiment", "analysis", "data_code"],
    },
    "scope_calibration": {
        "definition": "Adjust claims to the demonstrated evidence when reviewers challenge generalization or overreach.",
        "examples": ["Narrow a broad claim to the tested population or dataset."],
        "evidence_cues": ["scope", "generalization", "narrowed"],
    },
    "mechanism_explanation": {
        "definition": "Answer mechanism or ablation concerns by making causal, component, or feature contribution evidence explicit.",
        "examples": ["Add ablation and feature-importance explanation for model behavior."],
        "evidence_cues": ["ablation", "mechanism", "feature importance"],
    },
    "reproducibility_packaging": {
        "definition": "Convert reproducibility criticism into precise data, code, parameter, and protocol disclosures.",
        "examples": ["Release code, document parameters, and cite data repositories."],
        "evidence_cues": ["code", "dataset", "reproducibility"],
    },
    "presentation_repair": {
        "definition": "Resolve clarity and presentation concerns with targeted edits while avoiding over-claiming substantive changes.",
        "examples": ["Improve figure readability and clarify ambiguous wording."],
        "evidence_cues": ["clarify", "figure", "legend"],
    },
}


def build_taxonomy_artifacts() -> dict[str, dict[str, Any]]:
    return {
        "concern_taxonomy.v1.json": _taxonomy(
            "concern_taxonomy",
            "Reviewer concern labels used by rule_based_v1 reviewer annotation.",
            CONCERN_LABELS,
        ),
        "response_strategy_taxonomy.v1.json": _taxonomy(
            "response_strategy_taxonomy",
            "Author response strategy labels used by rule_based_v1 author annotation.",
            RESPONSE_STRATEGY_LABELS,
        ),
        "skill_taxonomy.v1.json": _taxonomy(
            "skill_taxonomy",
            "Reusable rebuttal skill families induced from aligned reviewer-author interactions.",
            SKILL_LABELS,
        ),
    }


def _taxonomy(name: str, description: str, labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "taxonomy_name": name,
        "taxonomy_version": TAXONOMY_VERSION,
        "description": description,
        "labels": {
            label: {
                "label": label,
                "definition": payload["definition"],
                "examples": list(payload["examples"]),
                "evidence_cues": list(payload["evidence_cues"]),
            }
            for label, payload in labels.items()
        },
    }
