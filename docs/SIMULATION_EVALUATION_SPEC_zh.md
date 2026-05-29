# Simulation Evaluation Spec

## Purpose

This document defines the Layer 5 simulation/evaluation artifact for NatureReview-Interact. It is a research-only evaluation scaffold over recorded workflow traces, not real peer review.

It is not RAG-only. Retrieval is used as support infrastructure; the simulation evaluates 跨学科价值: tacit knowledge boundary, institutional dependence, actor-network alignment, fast/slow cognitive correction, emotion-tone-commitment calibration, and author agency.

## Reviewer Agent

Input: workflow trace, concern map, response adequacy report, provenance.

Output:

- observable reviewer concern
- concern type and implicit risk probe
- coverage status
- unresolved concerns
- missing evidence actions

Forbidden:

- infer private reviewer psychology
- identify reviewers
- invent criticism not grounded in the review text

## Author Rebuttal Agent

Input: retrieved case explanations, evidence action plan, rebuttal plan, tone/commitment warnings.

Output:

- plan-first rebuttal scaffold
- author confirmation questions
- evidence actions and required artifacts
- case-transfer notes

Forbidden:

- generate final submission-ready rebuttal as the default artifact
- invent experiments, data, citations, or completed manuscript changes
- commit to changes the author has not verified

## Editor Signal Agent

Input: institutional signal, response adequacy, missing evidence actions, unresolved concerns.

Output:

- editor-readable unresolved-risk note
- revision pressure signal
- decision-boundary warning

Forbidden:

- predict acceptance probability
- simulate a real editor decision
- claim causal effects from historical cases

## Evaluation Signals

- concern coverage
- evidence grounding
- commitment safety
- case provenance completeness
- workflow provenance completeness
- cross-disciplinary trace coverage
- cross-disciplinary lens coverage
- forbidden behavior avoidance

## Boundary

All simulation traces are `model_assisted_not_human_gold`. They are useful for system debugging and evaluation design, but they are not human gold and not real peer review.

## Not RAG-only Boundary

The system must not 把检索结果当成最终答案, must not 用不可追溯的捷径替代案例证据和模型复核, must not 预测接收率, and must not 编造实验或承诺.
