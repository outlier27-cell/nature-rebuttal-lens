# Workflow v2 Report

## Input

- trace_count: 50
- source: Review Interaction KB v1 candidate units

## Agent steps

The workflow follows `understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output`.

## Retrieval metrics

Retrieval case IDs are attached per trace when available.

## Integrity checks

- no acceptance prediction
- no unverified experiment claim
- provenance required

## Cognitive trace quality

Every trace records all required slow-thinking stages.

## Institutional positioning

Every trace contains an `institutional_signal_note`.

## Actor-network alignment

Every trace contains `actor_network_note` derived from observable actor links.

## Failure cases

No execution errors in this generated batch. Labels remain candidate labels.

## Difference from direct rebuttal generation

The workflow outputs structured maps, evidence plans, warnings, and outlines. It does not produce a final submission-ready rebuttal.

## Limitations

This is not a final rebuttal-writing system and not a human-gold evaluation.
