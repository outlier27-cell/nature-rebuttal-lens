import os
from collections.abc import Mapping


DEFAULT_OPENAI_COMPATIBLE_BASE_URL = "https://xh.v1api.cc"
DEFAULT_OPENAI_COMPATIBLE_MODEL = "deepseek-v3"


class ModelProvider:
    provider_name = "provider"

    def describe(self) -> str:
        return self.provider_name

    def is_configured(self, env: Mapping[str, str] | None = None) -> bool:
        return True

    def model_capabilities(self) -> dict[str, str]:
        return {
            "annotation": "none",
            "alignment": "none",
            "judging": "none",
            "structured_output": "none",
        }

    def api_execution_wired(self) -> bool:
        return False


class RuleBasedProvider(ModelProvider):
    provider_name = "rule_based"

    def describe(self) -> str:
        return "legacy local baseline provider; no external model API required"

    def model_capabilities(self) -> dict[str, str]:
        return {
            "annotation": "rules",
            "alignment": "rules",
            "judging": "rules",
            "structured_output": "local_json",
        }


class ExternalAPIProvider(ModelProvider):
    provider_name = "external_api"

    def __init__(
        self,
        base_url: str = "",
        api_key_env: str = "PEER_REVIEW_API_KEY",
        model: str = "",
    ):
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.model = model

    @classmethod
    def from_environment(cls, env: Mapping[str, str] | None = None) -> "ExternalAPIProvider":
        environment = env if env is not None else os.environ
        return cls(
            base_url=environment.get("PEER_REVIEW_API_BASE_URL", DEFAULT_OPENAI_COMPATIBLE_BASE_URL),
            api_key_env="PEER_REVIEW_API_KEY",
            model=environment.get("PEER_REVIEW_API_MODEL", DEFAULT_OPENAI_COMPATIBLE_MODEL),
        )

    def describe(self) -> str:
        model = self.model or "not configured"
        return f"external model API provider at {self.base_url}; model: {model}; key env: {self.api_key_env}"

    def is_configured(self, env: Mapping[str, str] | None = None) -> bool:
        environment = env if env is not None else os.environ
        return (
            bool(self.base_url.strip())
            and bool(self.model.strip())
            and bool(environment.get(self.api_key_env, "").strip())
        )

    def model_capabilities(self) -> dict[str, str]:
        return {
            "annotation": "api",
            "alignment": "api",
            "judging": "api",
            "structured_output": "api",
        }

    def api_execution_wired(self) -> bool:
        return bool(self.base_url.strip()) and bool(self.model.strip())

    def create_client(self):
        environment = os.environ
        if not self.is_configured(environment):
            raise ValueError(
                f"external API provider is not configured; set {self.api_key_env}, "
                "PEER_REVIEW_API_BASE_URL, and PEER_REVIEW_API_MODEL"
            )
        from peer_review_skills.api.openai_compatible import OpenAICompatibleChatClient
        timeout_raw = environment.get("PEER_REVIEW_API_TIMEOUT_SECONDS", "120").strip()
        try:
            timeout_seconds = int(timeout_raw)
        except ValueError as exc:
            raise ValueError("PEER_REVIEW_API_TIMEOUT_SECONDS must be an integer") from exc
        if timeout_seconds <= 0:
            raise ValueError("PEER_REVIEW_API_TIMEOUT_SECONDS must be > 0")
        retry_raw = environment.get("PEER_REVIEW_API_TIMEOUT_RETRY_COUNT", "1").strip()
        try:
            timeout_retry_count = int(retry_raw)
        except ValueError as exc:
            raise ValueError("PEER_REVIEW_API_TIMEOUT_RETRY_COUNT must be an integer") from exc
        if timeout_retry_count < 0:
            raise ValueError("PEER_REVIEW_API_TIMEOUT_RETRY_COUNT must be >= 0")

        return OpenAICompatibleChatClient(
            base_url=self.base_url,
            api_key=environment[self.api_key_env],
            model=self.model,
            timeout_seconds=timeout_seconds,
            timeout_retry_count=timeout_retry_count,
        )
