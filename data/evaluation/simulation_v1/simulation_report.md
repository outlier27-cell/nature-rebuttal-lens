# Simulation v1 Report

## Scope

- trace_count: 50
- roles: reviewer_agent, author_rebuttal_agent, editor_signal_agent
- label_status: model_assisted_not_human_gold
- boundary: not real peer review

## Purpose

This layer evaluates whether a workflow trace can be re-read from three roles:

- Reviewer Agent: checks concern coverage against observable review text.
- Author Rebuttal Agent: checks evidence planning, confirmation questions, and case transfer.
- Editor Signal Agent: checks unresolved-risk signals without predicting acceptance.

## Limits

The simulation is not a replacement for real peer review, user studies, or human gold annotation.
