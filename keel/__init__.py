"""Keel: a reliability harness for open-weight models."""

from .agent import Agent, AgentRun, Tool
from .client import Backend, BackendError, GeminiBackend, OpenAICompatBackend, backend_from_env
from .extract import ExtractError, extract_json, iter_json
from .graph import CHANGE_PLAN_SCHEMA, CodeGraph, grounded_plan_verifier
from .harness import Attempt, Result, structured

__all__ = [
    "Agent",
    "AgentRun",
    "Attempt",
    "Backend",
    "BackendError",
    "CHANGE_PLAN_SCHEMA",
    "CodeGraph",
    "ExtractError",
    "GeminiBackend",
    "OpenAICompatBackend",
    "Result",
    "Tool",
    "backend_from_env",
    "extract_json",
    "grounded_plan_verifier",
    "iter_json",
    "structured",
]

__version__ = "0.1.0"
