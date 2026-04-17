"""Tool definitions exposed to the inner agent, and their handlers."""

from __future__ import annotations

from harness.state import AgentState

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "read_notes",
        "description": (
            "Read all notes you have written in prior sessions. "
            "Returns your accumulated notes, numbered sequentially."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "write_notes",
        "description": (
            "Append a note for your future self. Write down key findings, "
            "hypotheses, and important facts you want to remember."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The note to save.",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "read_case_file",
        "description": (
            "Read a specific section of the case file. "
            "Provide the section name to retrieve its contents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "The section name to read.",
                },
            },
            "required": ["section"],
        },
    },
    {
        "name": "query_environment",
        "description": (
            "Ask a factual question about the case environment. "
            "You may get an answer from records not in the case file, "
            "or a 'no information available' response."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Your question.",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "log_conclusion",
        "description": (
            "Commit a formal conclusion to the permanent record. "
            "Use this only when you have sufficient evidence. "
            "Conclusions are numbered and cannot be retracted, "
            "only superseded by later conclusions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The conclusion and supporting evidence.",
                },
            },
            "required": ["text"],
        },
    },
]


def handle_tool_call(
    name: str, input_data: dict, state: AgentState
) -> str:
    """Execute a tool call against ground-truth state. Returns the real result."""
    match name:
        case "read_notes":
            return state.read_notes()
        case "write_notes":
            return state.write_notes(input_data["text"])
        case "read_case_file":
            return state.read_case_section(input_data["section"])
        case "query_environment":
            return state.query_environment(input_data["question"])
        case "log_conclusion":
            return state.log_conclusion(input_data["text"])
        case _:
            return f"Unknown tool: {name}"
