"""Comprehensive experiment logger — captures everything for post-hoc analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RoundLog:
    round_num: int
    agent_output: str = ""
    messages: list[Any] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    pre_attack_state: dict = field(default_factory=dict)
    post_attack_state: dict = field(default_factory=dict)
    attack_results: list[dict] = field(default_factory=dict)
    detection_signals: dict = field(default_factory=dict)
    turns_used: int = 0


def _serialize(obj: Any) -> Any:
    """Make dataclass / anthropic objects JSON-safe."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    return str(obj)


class ExperimentLogger:
    def __init__(self, output_dir: str, experiment_name: str):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(output_dir) / f"{experiment_name}_{ts}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.rounds_dir = self.run_dir / "rounds"
        self.rounds_dir.mkdir()
        self._round_logs: list[RoundLog] = []
        print(f"Logging to {self.run_dir}")

    def log_config(self, config: Any) -> None:
        out = {
            "case_file_path": config.case_file_path,
            "num_rounds": config.num_rounds,
            "max_turns_per_round": config.max_turns_per_round,
            "model": config.model,
            "adversarial_awareness": config.adversarial_awareness,
            "attacks": [a.serialize() for a in config.attacks],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        (self.run_dir / "config.json").write_text(
            json.dumps(out, indent=2, default=_serialize)
        )

    def log_round(self, rlog: RoundLog) -> None:
        self._round_logs.append(rlog)
        path = self.rounds_dir / f"round_{rlog.round_num:03d}.json"

        # Strip raw Anthropic message objects — keep only serializable parts
        messages_safe = []
        for msg in rlog.messages:
            if isinstance(msg, dict):
                messages_safe.append(msg)
            else:
                messages_safe.append(str(msg))

        data = {
            "round_num": rlog.round_num,
            "turns_used": rlog.turns_used,
            "agent_output": rlog.agent_output,
            "tool_calls": rlog.tool_calls,
            "pre_attack_state": rlog.pre_attack_state,
            "post_attack_state": rlog.post_attack_state,
            "attack_results": [
                ar if isinstance(ar, dict) else asdict(ar)
                for ar in rlog.attack_results
            ],
            "detection_signals": rlog.detection_signals,
            "messages": messages_safe,
        }
        path.write_text(json.dumps(data, indent=2, default=_serialize))

        detected = any(
            s.get("detected") for s in rlog.detection_signals.values()
        )
        flag = " ** DETECTED **" if detected else ""
        print(
            f"  Round {rlog.round_num:2d}  "
            f"turns={rlog.turns_used:2d}  "
            f"tools={len(rlog.tool_calls):2d}  "
            f"conclusions={len(rlog.post_attack_state.get('conclusions', []))}"
            f"{flag}"
        )

    def finalize(self) -> None:
        summary = {
            "total_rounds": len(self._round_logs),
            "rounds_with_detection": sum(
                1
                for r in self._round_logs
                if any(
                    s.get("detected")
                    for s in r.detection_signals.values()
                )
            ),
            "total_tool_calls": sum(
                len(r.tool_calls) for r in self._round_logs
            ),
            "total_conclusions": max(
                (
                    len(r.post_attack_state.get("conclusions", []))
                    for r in self._round_logs
                ),
                default=0,
            ),
            "detection_timeline": {
                r.round_num: {
                    k: v
                    for k, v in r.detection_signals.items()
                    if v.get("detected")
                }
                for r in self._round_logs
                if any(
                    s.get("detected")
                    for s in r.detection_signals.values()
                )
            },
        }
        (self.run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, default=_serialize)
        )
        print(f"\nExperiment complete. Results in {self.run_dir}/")
        print(
            f"  Rounds with detection: "
            f"{summary['rounds_with_detection']}/{summary['total_rounds']}"
        )
