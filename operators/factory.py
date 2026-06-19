# -*- coding: utf-8 -*-
# Operator factory — builds LLM instances from AgenticDesignSpecs

from scripts.async_llm import AsyncLLM, LLMsConfig
from models import AgenticDesignSpecs, ModelRoleConfig


def _build_llm(role_config: ModelRoleConfig, role: str) -> AsyncLLM:
    """Build an AsyncLLM instance from a ModelRoleConfig, overriding temperature.

    Stamps `_role` onto the underlying LLMConfig so per-call tracking
    (call_tracking.install_call_tracking) can identify which role each call
    came from. The role tag rides on the config rather than the AsyncLLM
    because Workflow re-instantiates AsyncLLM around the same LLMConfig on
    every evaluation, but the LLMConfig itself is reused.
    """
    base_config = LLMsConfig.default().get(role_config.model_name)
    base_config.temperature = role_config.temperature
    base_config._role = role
    return AsyncLLM(base_config)


def build_role_llms(specs: AgenticDesignSpecs) -> dict:
    """Build AsyncLLM instances for each role defined in the agentic design specs."""
    return {
        "optimizer": _build_llm(specs.optimizer, "optimizer"),
        "aggregator": _build_llm(specs.aggregator, "aggregator"),
        "worker": _build_llm(specs.worker, "worker"),
    }
