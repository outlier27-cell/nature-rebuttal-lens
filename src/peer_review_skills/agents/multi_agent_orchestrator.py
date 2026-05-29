"""
Multi-Agent Orchestrator

Manages execution of multiple agents in a coordinated workflow.
Handles layer-based execution, message passing, and refinement loops.
"""

import json
from pathlib import Path
from typing import Any, Optional

from peer_review_skills.agents.base import AgentMessage, BaseAgent


class MultiAgentOrchestrator:
    """
    Orchestrates multi-agent workflow execution.

    Features:
    - Dependency-aware execution over the 5 capability layers
    - Message bus for agent communication
    - Refinement loops with downstream propagation and integrity recheck
    - Execution tracing and debugging
    """

    def __init__(
        self,
        agents: dict[str, BaseAgent],
        enable_refinement: bool = False,
        max_refinement_iterations: int = 2
    ):
        self.agents = agents
        self.enable_refinement = enable_refinement
        self.max_refinement_iterations = max_refinement_iterations
        self.message_bus: list[AgentMessage] = []
        self.execution_trace: list[dict[str, Any]] = []
        self._refinement_iteration_count = 0
        self._agent_input_history: dict[str, dict[str, Any]] = {}

    def execute_layer(
        self,
        layer_name: str,
        agent_ids: list[str],
        inputs: dict[str, Any]
    ) -> dict[str, AgentMessage]:
        """
        Execute all agents in a layer.

        Args:
            layer_name: Name of the layer (for tracing)
            agent_ids: List of agent IDs to execute
            inputs: Input data for all agents in this layer

        Returns:
            Dictionary mapping agent_id to AgentMessage
        """
        results = {}
        errors = []

        for agent_id in agent_ids:
            if agent_id not in self.agents:
                errors.append(f"Agent {agent_id} not found")
                continue

            try:
                agent = self.agents[agent_id]
                self._agent_input_history[agent_id] = dict(inputs)
                message = agent.execute(inputs)
                self.message_bus.append(message)
                results[agent_id] = message
            except Exception as e:
                errors.append(f"Agent {agent_id} failed: {str(e)}")

        # Record layer execution
        self.execution_trace.append({
            "layer": layer_name,
            "agents": agent_ids,
            "success_count": len(results),
            "error_count": len(errors),
            "errors": errors
        })

        if errors:
            raise RuntimeError(f"Layer {layer_name} failed: {errors}")

        return results

    def execute_workflow(
        self,
        unit: dict[str, Any],
        retrieval: dict[str, Any],
        taxonomies: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute the full 5-capability-layer multi-agent workflow.

        Args:
            unit: Interaction unit with review/response texts
            retrieval: Retrieval results with top_k cases
            taxonomies: Taxonomy definitions

        Returns:
            Complete workflow trace with all agent outputs
        """
        # Reset state
        self.message_bus = []
        self.execution_trace = []
        self._refinement_iteration_count = 0
        self._agent_input_history = {}

        # Layer 1a: explicit reviewer-understanding step.
        layer1_inputs = {
            "review_text": unit.get("review_text", ""),
            "taxonomies": taxonomies,
            "unit_id": unit.get("unit_id", "unknown")
        }
        reviewer_results = self.execute_layer(
            "Layer 1: Reviewer Understanding",
            ["reviewer_understanding_agent"],
            layer1_inputs
        )
        tacit_inputs = {
            **layer1_inputs,
            "concern_map": reviewer_results["reviewer_understanding_agent"].content,
        }
        tacit_results = self.execute_layer(
            "Layer 1: Tacit Concern Interpretation",
            ["tacit_concern_interpreter"],
            tacit_inputs,
        )
        layer1_results = {**reviewer_results, **tacit_results}

        # Layer 2: Strategy & Evidence
        layer2_inputs = {
            **layer1_inputs,
            "concern_map": layer1_results["reviewer_understanding_agent"].content,
            "risk_interpretation": layer1_results["tacit_concern_interpreter"].content,
            "retrieved_cases": retrieval.get("top_k", [])
        }
        layer2_results = self.execute_layer(
            "Layer 2: Strategy & Evidence",
            ["institutional_signal_interpreter", "evidence_action_planner"],
            layer2_inputs
        )

        # Layer 3a: author positioning must run before tone/commitment calibration.
        positioning_inputs = {
            **layer2_inputs,
            "response_text": unit.get("response_text", ""),
            "institutional_signal": layer2_results["institutional_signal_interpreter"].content,
            "evidence_plan": layer2_results["evidence_action_planner"].content
        }
        positioning_results = self.execute_layer(
            "Layer 3: Author Positioning",
            ["author_positioning_agent"],
            positioning_inputs,
        )
        tone_inputs = {
            **positioning_inputs,
            "author_positioning": positioning_results["author_positioning_agent"].content,
        }
        tone_results = self.execute_layer(
            "Layer 3: Tone & Commitment",
            ["tone_commitment_calibrator"],
            tone_inputs,
        )
        layer3_inputs = tone_inputs
        layer3_results = {**positioning_results, **tone_results}

        # Layer 4: Network & Context
        prior_agent_outputs = {
            **{k: v.content for k, v in layer1_results.items()},
            **{k: v.content for k, v in layer2_results.items()},
            **{k: v.content for k, v in layer3_results.items()},
        }
        layer4_inputs = {
            **layer3_inputs,
            "author_positioning": layer3_results["author_positioning_agent"].content,
            "tone_calibration": layer3_results["tone_commitment_calibrator"].content,
            "all_agent_outputs": prior_agent_outputs,
            "unit": unit,
            "retrieval": retrieval,
        }
        actor_network_results = self.execute_layer(
            "Layer 4: Actor Network",
            ["actor_network_mapper"],
            layer4_inputs
        )
        lens_inputs = {
            **layer4_inputs,
            "all_agent_outputs": {
                **prior_agent_outputs,
                **{k: v.content for k, v in actor_network_results.items()},
            },
        }
        layer4_results = {
            **actor_network_results,
            **self.execute_layer(
                "Layer 4: Cross-Disciplinary Lenses",
                ["cross_disciplinary_lens_interpreter"],
                lens_inputs,
            ),
        }

        # Layer 5: Integrity
        all_agent_outputs = {
            **{k: v.content for k, v in layer1_results.items()},
            **{k: v.content for k, v in layer2_results.items()},
            **{k: v.content for k, v in layer3_results.items()},
            **{k: v.content for k, v in layer4_results.items()},
        }
        layer5_inputs = {
            "all_agent_outputs": all_agent_outputs,
            "unit": unit,
            "retrieval": retrieval
        }
        layer5_results = self.execute_layer(
            "Layer 5: Integrity",
            ["integrity_adequacy_checker"],
            layer5_inputs
        )

        # Check if refinement is needed
        final_integrity_output = layer5_results["integrity_adequacy_checker"].content
        if self.enable_refinement:
            integrity_output = final_integrity_output
            while (
                self._needs_refinement(integrity_output)
                and self._refinement_iteration_count < self.max_refinement_iterations
            ):
                self._refinement_iteration_count += 1
                refined_results = self._execute_refinement_iteration(
                    all_agent_outputs,
                    integrity_output,
                    self._refinement_iteration_count,
                )
                all_agent_outputs.update(refined_results)
                propagated_results = self._propagate_refined_outputs(
                    refined_results,
                    all_agent_outputs,
                    unit,
                    retrieval,
                    taxonomies,
                    self._refinement_iteration_count,
                )
                all_agent_outputs.update(propagated_results)
                recheck_results = self.execute_layer(
                    f"Layer 5: Integrity Recheck {self._refinement_iteration_count}",
                    ["integrity_adequacy_checker"],
                    {
                        "all_agent_outputs": all_agent_outputs,
                        "unit": unit,
                        "retrieval": retrieval,
                        "refinement_context": {
                            "iteration": self._refinement_iteration_count,
                            "previous_integrity_output": integrity_output,
                            "refined_agent_ids": sorted(refined_results),
                        },
                    },
                )
                integrity_output = recheck_results["integrity_adequacy_checker"].content
                final_integrity_output = integrity_output

            if self._needs_refinement(final_integrity_output):
                raise RuntimeError(
                    "Refinement did not resolve critical integrity issues "
                    f"after {self.max_refinement_iterations} iterations"
                )

        # Assemble final output
        return {
            "trace_id": f"workflow_v3_{unit.get('unit_id', 'unknown')}",
            "query_unit_id": unit.get("unit_id", "unknown"),
            "agent_intermediate_outputs": {
                **all_agent_outputs,
                "integrity_adequacy_checker": final_integrity_output
            },
            "message_bus": [msg.to_dict() for msg in self.message_bus],
            "execution_trace": self.execution_trace,
            "execution_metadata": {
                "total_llm_calls": len(self.message_bus),
                "layers_executed": len(self.execution_trace),
                "agents_executed": len(self.agents),
                "refinement_enabled": self.enable_refinement,
                "refinement_iterations": self._count_refinement_iterations()
            }
        }

    def execute_rebuttal_lens_workflow(
        self,
        unit: dict[str, Any],
        retrieval: dict[str, Any],
        taxonomies: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the 12-agent manuscript-aware RebuttalLens workflow."""
        self.message_bus = []
        self.execution_trace = []
        self._refinement_iteration_count = 0
        self._agent_input_history = {}

        base_inputs = {
            "review_text": unit.get("review_text", ""),
            "response_text": unit.get("response_text", ""),
            "editor_text": unit.get("editor_text", ""),
            "taxonomies": taxonomies,
            "unit_id": unit.get("unit_id", "unknown"),
            "unit": unit,
            "retrieval": retrieval,
            "manuscript_context": unit.get("manuscript_context", {}),
        }

        manuscript_context_results = self.execute_layer(
            "Layer 0: Manuscript Context",
            ["manuscript_context_extractor"],
            base_inputs,
        )
        reviewer_results = self.execute_layer(
            "Layer 1: Reviewer Understanding",
            ["reviewer_understanding_agent"],
            {
                **base_inputs,
                "manuscript_context_note": manuscript_context_results[
                    "manuscript_context_extractor"
                ].content,
            },
        )
        tacit_results = self.execute_layer(
            "Layer 1: Tacit Concern Interpretation",
            ["tacit_concern_interpreter"],
            {
                **base_inputs,
                "manuscript_context_note": manuscript_context_results[
                    "manuscript_context_extractor"
                ].content,
                "concern_map": reviewer_results["reviewer_understanding_agent"].content,
            },
        )
        manuscript_evidence_results = self.execute_layer(
            "Layer 1: Manuscript Evidence",
            ["manuscript_evidence_locator"],
            {
                **base_inputs,
                "manuscript_context_note": manuscript_context_results[
                    "manuscript_context_extractor"
                ].content,
                "concern_map": reviewer_results["reviewer_understanding_agent"].content,
            },
        )
        institutional_results = self.execute_layer(
            "Layer 2: Institutional Signal",
            ["institutional_signal_interpreter"],
            {
                **base_inputs,
                "concern_map": reviewer_results["reviewer_understanding_agent"].content,
                "manuscript_evidence": manuscript_evidence_results[
                    "manuscript_evidence_locator"
                ].content,
            },
        )
        case_results = self.execute_layer(
            "Layer 2: Case Retrieval Interpretation",
            ["case_retrieval_interpreter"],
            {
                **base_inputs,
                "concern_map": reviewer_results["reviewer_understanding_agent"].content,
                "risk_interpretation": tacit_results["tacit_concern_interpreter"].content,
                "retrieved_cases": retrieval.get("top_k", []),
                "manuscript_evidence": manuscript_evidence_results[
                    "manuscript_evidence_locator"
                ].content,
            },
        )
        evidence_results = self.execute_layer(
            "Layer 2: Evidence Action Planning",
            ["evidence_action_planner"],
            {
                **base_inputs,
                "concern_map": reviewer_results["reviewer_understanding_agent"].content,
                "risk_interpretation": tacit_results["tacit_concern_interpreter"].content,
                "retrieved_cases": retrieval.get("top_k", []),
                "manuscript_evidence": manuscript_evidence_results[
                    "manuscript_evidence_locator"
                ].content,
                "case_interpretation": case_results["case_retrieval_interpreter"].content,
            },
        )
        positioning_results = self.execute_layer(
            "Layer 3: Author Positioning",
            ["author_positioning_agent"],
            {
                **base_inputs,
                "institutional_signal": institutional_results[
                    "institutional_signal_interpreter"
                ].content,
                "evidence_plan": evidence_results["evidence_action_planner"].content,
                "manuscript_evidence": manuscript_evidence_results[
                    "manuscript_evidence_locator"
                ].content,
            },
        )
        tone_results = self.execute_layer(
            "Layer 3: Tone & Commitment",
            ["tone_commitment_calibrator"],
            {
                **base_inputs,
                "evidence_plan": evidence_results["evidence_action_planner"].content,
                "author_positioning": positioning_results["author_positioning_agent"].content,
                "manuscript_evidence": manuscript_evidence_results[
                    "manuscript_evidence_locator"
                ].content,
            },
        )
        prior_outputs = {
            **{k: v.content for k, v in manuscript_context_results.items()},
            **{k: v.content for k, v in reviewer_results.items()},
            **{k: v.content for k, v in tacit_results.items()},
            **{k: v.content for k, v in manuscript_evidence_results.items()},
            **{k: v.content for k, v in institutional_results.items()},
            **{k: v.content for k, v in case_results.items()},
            **{k: v.content for k, v in evidence_results.items()},
            **{k: v.content for k, v in positioning_results.items()},
            **{k: v.content for k, v in tone_results.items()},
        }
        actor_results = self.execute_layer(
            "Layer 4: Actor Network",
            ["actor_network_mapper"],
            {
                **base_inputs,
                "evidence_plan": evidence_results["evidence_action_planner"].content,
                "retrieved_cases": retrieval.get("top_k", []),
                "author_positioning": positioning_results["author_positioning_agent"].content,
                "tone_calibration": tone_results["tone_commitment_calibrator"].content,
                "manuscript_evidence": manuscript_evidence_results[
                    "manuscript_evidence_locator"
                ].content,
                "all_agent_outputs": prior_outputs,
            },
        )
        lens_results = self.execute_layer(
            "Layer 4: Cross-Disciplinary Lenses",
            ["cross_disciplinary_lens_interpreter"],
            {
                **base_inputs,
                "all_agent_outputs": {
                    **prior_outputs,
                    **{k: v.content for k, v in actor_results.items()},
                },
            },
        )
        all_agent_outputs = {
            **prior_outputs,
            **{k: v.content for k, v in actor_results.items()},
            **{k: v.content for k, v in lens_results.items()},
        }
        integrity_results = self.execute_layer(
            "Layer 5: Integrity",
            ["integrity_adequacy_checker"],
            {
                "all_agent_outputs": all_agent_outputs,
                "unit": unit,
                "retrieval": retrieval,
                "manuscript_context": unit.get("manuscript_context", {}),
            },
        )
        final_integrity_output = integrity_results["integrity_adequacy_checker"].content
        all_agent_outputs["integrity_adequacy_checker"] = final_integrity_output

        return {
            "trace_id": f"rebuttal_lens_{unit.get('unit_id', 'unknown')}",
            "query_unit_id": unit.get("unit_id", "unknown"),
            "agent_intermediate_outputs": all_agent_outputs,
            "message_bus": [msg.to_dict() for msg in self.message_bus],
            "execution_trace": self.execution_trace,
            "execution_metadata": {
                "total_llm_calls": len(self.message_bus),
                "layers_executed": len(self.execution_trace),
                "agents_executed": len(all_agent_outputs),
                "refinement_enabled": self.enable_refinement,
                "refinement_iterations": self._count_refinement_iterations(),
                "manuscript_mode": unit.get("manuscript_context", {}).get("mode"),
            },
        }

    def _needs_refinement(self, integrity_output: dict[str, Any]) -> bool:
        """Check if refinement is needed based on integrity check"""
        issues = integrity_output.get("issues", [])
        critical_issues = [
            issue for issue in issues
            if issue.get("severity") == "critical"
        ]
        return len(critical_issues) > 0

    def _execute_refinement_iteration(
        self,
        agent_outputs: dict[str, Any],
        integrity_output: dict[str, Any],
        iteration: int,
    ) -> dict[str, Any]:
        """Execute one refinement iteration for agents with critical issues."""
        refined = {}
        issues = [
            issue
            for issue in integrity_output.get("issues", [])
            if issue.get("severity") == "critical"
        ]
        unrefinable = [
            issue
            for issue in issues
            if not issue.get("agent_id") or issue.get("agent_id") not in self.agents
        ]
        if unrefinable:
            raise RuntimeError(
                "Integrity check returned unrefinable critical integrity issues: "
                f"{unrefinable}"
            )
        refined_agent_ids = []

        for issue in issues:
            agent_id = issue.get("agent_id")
            if not agent_id or agent_id not in self.agents:
                continue

            # Build refinement request
            refinement_request = {
                "feedback": issue.get("description", ""),
                "issues": [issue],
                "previous_output": agent_outputs.get(agent_id, {}),
                "original_inputs": self._agent_input_history.get(agent_id, {}),
            }

            agent = self.agents[agent_id]
            refined_message = agent.refine(refinement_request)
            self.message_bus.append(refined_message)
            refined[agent_id] = refined_message.content
            refined_agent_ids.append(agent_id)

        self.execution_trace.append({
            "layer": f"Refinement Iteration {iteration}",
            "agents": refined_agent_ids,
            "success_count": len(refined_agent_ids),
            "error_count": 0,
            "errors": [],
            "source_integrity_issues": issues,
        })

        return refined

    def _propagate_refined_outputs(
        self,
        refined_results: dict[str, Any],
        agent_outputs: dict[str, Any],
        unit: dict[str, Any],
        retrieval: dict[str, Any],
        taxonomies: dict[str, Any],
        iteration: int,
    ) -> dict[str, Any]:
        """Rerun downstream agents whose inputs depend on refined outputs."""
        rerun_order = self._downstream_agents_for(sorted(refined_results))
        propagated: dict[str, Any] = {}

        for agent_id in rerun_order:
            inputs = self._build_agent_inputs(agent_id, unit, retrieval, taxonomies, agent_outputs)
            results = self.execute_layer(
                f"Refinement Propagation {iteration}: {agent_id}",
                [agent_id],
                inputs,
            )
            agent_outputs[agent_id] = results[agent_id].content
            propagated[agent_id] = results[agent_id].content

        self.execution_trace.append({
            "layer": f"Refinement Propagation {iteration}",
            "agents": rerun_order,
            "success_count": len(rerun_order),
            "error_count": 0,
            "errors": [],
            "refined_source_agents": sorted(refined_results),
        })
        return propagated

    def _downstream_agents_for(self, agent_ids: list[str]) -> list[str]:
        order = [
            "reviewer_understanding_agent",
            "tacit_concern_interpreter",
            "institutional_signal_interpreter",
            "evidence_action_planner",
            "author_positioning_agent",
            "tone_commitment_calibrator",
            "actor_network_mapper",
            "cross_disciplinary_lens_interpreter",
        ]
        downstream = {
            "reviewer_understanding_agent": {
                "tacit_concern_interpreter",
                "institutional_signal_interpreter",
                "evidence_action_planner",
                "author_positioning_agent",
                "tone_commitment_calibrator",
                "actor_network_mapper",
                "cross_disciplinary_lens_interpreter",
            },
            "tacit_concern_interpreter": {
                "institutional_signal_interpreter",
                "evidence_action_planner",
                "author_positioning_agent",
                "tone_commitment_calibrator",
                "actor_network_mapper",
                "cross_disciplinary_lens_interpreter",
            },
            "institutional_signal_interpreter": {
                "author_positioning_agent",
                "tone_commitment_calibrator",
                "actor_network_mapper",
                "cross_disciplinary_lens_interpreter",
            },
            "evidence_action_planner": {
                "author_positioning_agent",
                "tone_commitment_calibrator",
                "actor_network_mapper",
                "cross_disciplinary_lens_interpreter",
            },
            "author_positioning_agent": {
                "tone_commitment_calibrator",
                "actor_network_mapper",
                "cross_disciplinary_lens_interpreter",
            },
            "tone_commitment_calibrator": {
                "actor_network_mapper",
                "cross_disciplinary_lens_interpreter",
            },
            "actor_network_mapper": {"cross_disciplinary_lens_interpreter"},
            "cross_disciplinary_lens_interpreter": set(),
        }
        selected: set[str] = set()
        for agent_id in agent_ids:
            selected.update(downstream.get(agent_id, set()))
        return [agent_id for agent_id in order if agent_id in selected]

    def _build_agent_inputs(
        self,
        agent_id: str,
        unit: dict[str, Any],
        retrieval: dict[str, Any],
        taxonomies: dict[str, Any],
        agent_outputs: dict[str, Any],
    ) -> dict[str, Any]:
        base_inputs = {
            "review_text": unit.get("review_text", ""),
            "response_text": unit.get("response_text", ""),
            "taxonomies": taxonomies,
            "unit_id": unit.get("unit_id", "unknown"),
        }
        if agent_id == "reviewer_understanding_agent":
            return {
                "review_text": unit.get("review_text", ""),
                "taxonomies": taxonomies,
                "unit_id": unit.get("unit_id", "unknown"),
            }
        if agent_id == "tacit_concern_interpreter":
            return {
                **base_inputs,
                "concern_map": agent_outputs.get("reviewer_understanding_agent", {}),
            }
        if agent_id == "institutional_signal_interpreter":
            return {
                **base_inputs,
                "concern_map": agent_outputs.get("reviewer_understanding_agent", {}),
            }
        if agent_id == "evidence_action_planner":
            return {
                **base_inputs,
                "concern_map": agent_outputs.get("reviewer_understanding_agent", {}),
                "risk_interpretation": agent_outputs.get("tacit_concern_interpreter", {}),
                "retrieved_cases": retrieval.get("top_k", []),
            }
        if agent_id == "author_positioning_agent":
            return {
                **base_inputs,
                "institutional_signal": agent_outputs.get("institutional_signal_interpreter", {}),
                "evidence_plan": agent_outputs.get("evidence_action_planner", {}),
            }
        if agent_id == "tone_commitment_calibrator":
            return {
                **base_inputs,
                "evidence_plan": agent_outputs.get("evidence_action_planner", {}),
                "author_positioning": agent_outputs.get("author_positioning_agent", {}),
            }
        if agent_id == "actor_network_mapper":
            return {
                **base_inputs,
                "evidence_plan": agent_outputs.get("evidence_action_planner", {}),
                "retrieved_cases": retrieval.get("top_k", []),
                "author_positioning": agent_outputs.get("author_positioning_agent", {}),
                "tone_calibration": agent_outputs.get("tone_commitment_calibrator", {}),
                "all_agent_outputs": agent_outputs,
                "unit": unit,
                "retrieval": retrieval,
            }
        if agent_id == "cross_disciplinary_lens_interpreter":
            return {
                **base_inputs,
                "all_agent_outputs": agent_outputs,
                "unit": unit,
                "retrieval": retrieval,
            }
        raise ValueError(f"Cannot build inputs for unknown agent: {agent_id}")

    def _count_refinement_iterations(self) -> int:
        """Count number of refinement iterations executed"""
        return self._refinement_iteration_count

    def get_execution_summary(self) -> dict[str, Any]:
        """Get summary of workflow execution"""
        return {
            "total_messages": len(self.message_bus),
            "total_agents": len(self.agents),
            "layers_executed": len(self.execution_trace),
            "errors": [
                trace.get("errors", [])
                for trace in self.execution_trace
                if trace.get("errors")
            ],
            "execution_trace": self.execution_trace
        }

    def save_trace(self, output_path: Path) -> None:
        """Save execution trace to file"""
        trace_data = {
            "message_bus": [msg.to_dict() for msg in self.message_bus],
            "execution_trace": self.execution_trace,
            "summary": self.get_execution_summary()
        }
        output_path.write_text(
            json.dumps(trace_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


def create_orchestrator(
    agents: dict[str, BaseAgent],
    config: Optional[dict[str, Any]] = None
) -> MultiAgentOrchestrator:
    """
    Factory function to create orchestrator.

    Args:
        agents: Dictionary of agent_id -> BaseAgent
        config: Optional configuration dict

    Returns:
        Configured MultiAgentOrchestrator
    """
    config = config or {}
    return MultiAgentOrchestrator(
        agents=agents,
        enable_refinement=config.get("enable_refinement", False),
        max_refinement_iterations=config.get("max_refinement_iterations", 2)
    )
