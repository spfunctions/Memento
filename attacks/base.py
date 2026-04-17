"""Base interface for all attack plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from harness.state import AgentState


@dataclass
class AttackResult:
    attack_type: str
    round_num: int
    original: Any
    modified: Any
    intensity: float
    metadata: dict = field(default_factory=dict)


class Attack(ABC):
    """Every attack must implement apply() and detection_signal().

    Optionally override intercept_tool() to tamper with tool results
    in real time during a round.
    """

    name: str = "base"

    def __init__(self, intensity: float = 0.5):
        assert 0.0 <= intensity <= 1.0
        self.intensity = intensity

    @abstractmethod
    def apply(
        self, state: AgentState, round_num: int
    ) -> Optional[AttackResult]:
        """Mutate *state* between rounds. Return metadata or None if skipped."""

    @abstractmethod
    def detection_signal(self, agent_output: str) -> dict:
        """Scan agent text for signs it noticed tampering.

        Returns {"detected": bool, "indicators": [str, ...]}.
        """

    def intercept_tool(
        self,
        tool_name: str,
        tool_input: dict,
        real_result: str,
        state: AgentState,
        round_num: int,
    ) -> str:
        """Optionally modify a tool result before the agent sees it.

        Default: pass through unchanged.
        """
        return real_result

    def serialize(self) -> dict:
        return {"name": self.name, "intensity": self.intensity}
