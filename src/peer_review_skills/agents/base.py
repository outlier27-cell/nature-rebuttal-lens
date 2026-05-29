"""
Multi-Agent Framework Base Classes

This module provides the foundation for true multi-agent LLM systems.
Each agent is an independent reasoning unit with its own LLM calls.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class AgentMessage:
    """Message passed between agents"""

    agent_id: str
    timestamp: str
    message_type: str  # "output", "question", "refinement_request", "error"
    content: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentMessage":
        """Create from dictionary"""
        return cls(
            agent_id=data["agent_id"],
            timestamp=data["timestamp"],
            message_type=data["message_type"],
            content=data["content"],
            metadata=data.get("metadata", {}),
        )


class BaseAgent(ABC):
    """
    Base class for all LLM-based agents.

    Each agent:
    - Makes independent LLM calls
    - Has specialized prompts
    - Produces structured outputs
    - Can communicate with other agents
    """

    def __init__(
        self,
        agent_id: str,
        model_client: Any,
        temperature: float = 0.0,
        max_retries: int = 3
    ):
        self.agent_id = agent_id
        self.client = model_client
        self.temperature = temperature
        self.max_retries = max_retries
        self.message_history: list[AgentMessage] = []
        self.execution_count = 0

    @abstractmethod
    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        """
        Build LLM prompt from inputs.

        Returns:
            List of message dicts with "role" and "content" keys
        """
        pass

    @abstractmethod
    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        Parse LLM response into structured output.

        Args:
            response: Raw LLM API response

        Returns:
            Structured output dictionary
        """
        pass

    @abstractmethod
    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate agent output.

        Returns:
            (is_valid, error_message)
        """
        pass

    def execute(self, inputs: dict[str, Any]) -> AgentMessage:
        """
        Execute agent: build prompt, call LLM, parse and validate response.

        Args:
            inputs: Input data for the agent

        Returns:
            AgentMessage with agent output
        """
        self.execution_count += 1

        try:
            # Build prompt
            prompt = self.build_prompt(inputs)

            # Call LLM with retries
            response = self._call_llm_with_retry(prompt)

            # Parse response
            parsed = self.parse_response(response)

            # Validate output
            is_valid, error_msg = self.validate_output(parsed)
            if not is_valid:
                raise ValueError(f"Agent output validation failed: {error_msg}")

            # Create message
            message = AgentMessage(
                agent_id=self.agent_id,
                timestamp=datetime.now().isoformat(),
                message_type="output",
                content=parsed,
                metadata={
                    "model": getattr(self.client, "model_name", getattr(self.client, "model", "unknown")),
                    "temperature": self.temperature,
                    "execution_count": self.execution_count,
                    "prompt_tokens": response.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": response.get("usage", {}).get("completion_tokens", 0),
                }
            )

            self.message_history.append(message)
            return message

        except Exception as e:
            # Create error message
            error_message = AgentMessage(
                agent_id=self.agent_id,
                timestamp=datetime.now().isoformat(),
                message_type="error",
                content={"error": str(e)},
                metadata={"execution_count": self.execution_count}
            )
            self.message_history.append(error_message)
            raise

    def _call_llm_with_retry(self, prompt: list[dict[str, str]]) -> dict[str, Any]:
        """Call LLM with retry logic"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.create_chat_completion(
                    prompt,
                    response_format={"type": "json_object"},
                    temperature=self.temperature
                )
                return response
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Wait before retry (exponential backoff)
                    import time
                    time.sleep(2 ** attempt)
                continue

        raise RuntimeError(f"LLM call failed after {self.max_retries} attempts: {last_error}")

    def refine(self, refinement_request: dict[str, Any]) -> AgentMessage:
        """
        Refine previous output based on feedback.

        Args:
            refinement_request: Feedback and refinement instructions

        Returns:
            AgentMessage with refined output
        """
        # Get previous output
        previous_output = None
        for msg in reversed(self.message_history):
            if msg.message_type == "output":
                previous_output = msg.content
                break

        if previous_output is None:
            raise ValueError("No previous output to refine")

        # Build refinement prompt
        refinement_inputs = {
            **dict(refinement_request.get("original_inputs", {})),
            "previous_output": previous_output,
            "feedback": refinement_request.get("feedback", ""),
            "issues": refinement_request.get("issues", []),
        }

        # Execute with refinement context
        return self.execute(refinement_inputs)

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent (override in subclasses)"""
        return f"You are {self.agent_id}, a specialized agent in a multi-agent system."


def attach_refinement_context(
    payload: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """
    Include integrity-check feedback in an agent prompt without changing normal runs.

    Refinement must be auditable: the model should see the prior output, the
    integrity issue, and the requested correction while preserving the original
    task inputs.
    """
    if "feedback" not in inputs and "issues" not in inputs and "previous_output" not in inputs:
        return payload
    enriched = dict(payload)
    enriched["refinement_context"] = {
        "feedback": inputs.get("feedback", ""),
        "issues": inputs.get("issues", []),
        "previous_output": inputs.get("previous_output", {}),
        "instruction": (
            "Revise this agent output only where needed to address the integrity "
            "feedback. Preserve provenance, author confirmation, and responsible "
            "use boundaries."
        ),
    }
    return enriched


class LLMAgent(BaseAgent):
    """
    Concrete LLM agent with configurable prompts.

    Use this for quick agent creation without subclassing.
    """

    def __init__(
        self,
        agent_id: str,
        model_client: Any,
        system_prompt: str,
        output_schema: dict[str, Any],
        temperature: float = 0.0,
        max_retries: int = 3
    ):
        super().__init__(agent_id, model_client, temperature, max_retries)
        self.system_prompt = system_prompt
        self.output_schema = output_schema

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        """Build prompt with system message and user inputs"""
        return [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": json.dumps(inputs, ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Parse JSON response from LLM"""
        try:
            content = response["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse LLM response: {e}")

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate output against schema"""
        # Basic validation: check required keys
        required_keys = self.output_schema.get("required", [])
        missing_keys = [key for key in required_keys if key not in output]

        if missing_keys:
            return False, f"Missing required keys: {missing_keys}"

        return True, None

    def get_system_prompt(self) -> str:
        """Return configured system prompt"""
        return self.system_prompt


def create_agent(
    agent_id: str,
    model_client: Any,
    system_prompt: str,
    output_schema: dict[str, Any],
    **kwargs
) -> LLMAgent:
    """
    Factory function to create an LLM agent.

    Args:
        agent_id: Unique identifier for the agent
        model_client: LLM client (OpenAI-compatible)
        system_prompt: System prompt defining agent behavior
        output_schema: Expected output schema
        **kwargs: Additional arguments for LLMAgent

    Returns:
        Configured LLMAgent instance
    """
    return LLMAgent(
        agent_id=agent_id,
        model_client=model_client,
        system_prompt=system_prompt,
        output_schema=output_schema,
        **kwargs
    )


def parse_agent_json_response(response: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize agent LLM output to a JSON object.

    The test mock returns raw OpenAI chat-completion responses, while the
    repository's OpenAICompatibleChatClient returns the parsed JSON object.
    Agents use this helper so both paths share the same contract.
    """
    if not isinstance(response, dict):
        raise ValueError("LLM response must be a dictionary")

    if "choices" not in response:
        return response

    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Failed to parse raw chat completion response") from exc

    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise ValueError("Raw chat completion content is not a string or JSON object")

    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse LLM JSON response: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("LLM JSON response must be an object")
    return value
