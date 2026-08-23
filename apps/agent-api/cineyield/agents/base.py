"""Base interface for CineYield agents.

Real implementations will use Google ADK and Gemini.
Placeholders raise NotImplementedError to make missing implementations explicit.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """Shared context passed to every agent invocation."""
    asset_id: str | None = None
    scene_id: str | None = None
    opportunity_id: str | None = None
    campaign_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class BaseAgent(abc.ABC):
    """Abstract base for all CineYield pipeline agents."""

    name: str = ""

    @abc.abstractmethod
    async def run(self, ctx: AgentContext) -> dict[str, Any]:
        """Execute the agent and return a result dict."""

    @property
    def is_configured(self) -> bool:
        """Return True when all required credentials/config are available."""
        return False
