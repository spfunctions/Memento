"""Persistent state the inner agent reads and writes across rounds."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentState:
    case_file: dict[str, str]          # section_name -> text
    notes: list[str] = field(default_factory=list)
    conclusions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    environment_qa: dict[str, str] = field(default_factory=dict)

    # Ground truth, never mutated by attacks
    _original_case_file: dict[str, str] = field(
        default_factory=dict, repr=False
    )
    _original_environment_qa: dict[str, str] = field(
        default_factory=dict, repr=False
    )

    @classmethod
    def from_case_file(cls, path: str) -> AgentState:
        data = json.loads(Path(path).read_text())
        sections = data["sections"]
        qa = data.get("environment_qa", {})
        state = cls(
            case_file=copy.deepcopy(sections),
            metadata=data.get("metadata", {}),
            environment_qa=copy.deepcopy(qa),
        )
        state._original_case_file = copy.deepcopy(sections)
        state._original_environment_qa = copy.deepcopy(qa)
        return state

    def snapshot(self) -> dict:
        return {
            "case_file": copy.deepcopy(self.case_file),
            "notes": list(self.notes),
            "conclusions": list(self.conclusions),
        }

    # ── tool handlers ──────────────────────────────────────────────

    def read_notes(self) -> str:
        if not self.notes:
            return "(No notes from prior sessions.)"
        parts = []
        for i, note in enumerate(self.notes, 1):
            parts.append(f"--- Note {i} ---\n{note}")
        return "\n\n".join(parts)

    def write_notes(self, text: str) -> str:
        self.notes.append(text)
        return f"Note saved. You now have {len(self.notes)} note(s)."

    def read_case_section(self, section: str) -> str:
        if section in self.case_file:
            return self.case_file[section]
        available = ", ".join(sorted(self.case_file.keys()))
        return f"Section '{section}' not found. Available sections: {available}"

    def list_case_sections(self) -> str:
        return ", ".join(sorted(self.case_file.keys()))

    def query_environment(self, question: str) -> str:
        q_lower = question.lower().strip().rstrip("?")
        # Exact match first
        if question in self.environment_qa:
            return self.environment_qa[question]
        # Case-insensitive prefix match
        for key, answer in self.environment_qa.items():
            if q_lower in key.lower() or key.lower() in q_lower:
                return answer
        return (
            "No information available for that question. "
            "Try rephrasing or consult the case file sections."
        )

    def log_conclusion(self, text: str) -> str:
        self.conclusions.append(text)
        return (
            f"Conclusion #{len(self.conclusions)} committed to the record."
        )
