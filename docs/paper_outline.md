# Nature RebuttalLens Technical Report Outline

## Problem

Authors need rebuttal planning support that keeps reviewer concerns tied to manuscript evidence, author-confirmed actions, and responsible-use boundaries. The system is not an acceptance predictor and does not generate final submission text.

## System

Nature RebuttalLens uses a manuscript-aware multi-agent workflow. The core contract is an evidence ledger: every concern card must point to a ledger row, manuscript span, evidence status, case analogy boundary, required author action, unsafe claim boundary, and author confirmation state.

## Evaluation

The evaluation plan combines an OpenReview/Re^2-style benchmark adapter, human-calibrated benchmark sheets, ablation-ready system labels, and judge calibration. Human-calibrated benchmark claims must distinguish human gold, model-assisted labels, and diagnostic judge scores.

## Safety

The privacy gate blocks external manuscript upload unless the run explicitly sets consent. Each run writes a privacy manifest and reproducibility manifest. The report and HTML workspace preserve the assistant boundary and warn that all evidence and commitments require author verification.

## Reproducibility

The runtime manifest records git hash, config hash, model/provider identity, input hashes, workflow engine, and privacy manifest path. Trace replay rebuilds the final report without model calls, enabling schema-stable checks and downstream UI regression tests.

## Limitations

Current benchmark artifacts are model-assisted unless separately human-confirmed. Retrieved cases are analogies, not evidence about the current manuscript. The author workspace is for planning only and intentionally avoids producing final rebuttal prose.
