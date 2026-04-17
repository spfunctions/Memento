"""Outer harness: spawns Claude instances via `claude -p`, applies attacks, records everything."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field

from attacks.base import Attack, AttackResult
from .state import AgentState
from .logger import ExperimentLogger, RoundLog
from agent.prompts import build_full_prompt


@dataclass
class ExperimentConfig:
    case_file_path: str
    attacks: list[Attack] = field(default_factory=list)
    num_rounds: int = 10
    model: str = "sonnet"
    adversarial_awareness: bool = False
    output_dir: str = "runs"
    experiment_name: str = "experiment"


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.state = AgentState.from_case_file(config.case_file_path)
        self.logger = ExperimentLogger(
            config.output_dir, config.experiment_name
        )
        self.attacks = config.attacks

    def run(self) -> None:
        self.logger.log_config(self.config)
        label = "CONTROL" if not self.attacks else "EXPERIMENTAL"
        awareness = " (adversarial-aware)" if self.config.adversarial_awareness else ""
        print(
            f"\n{'='*60}\n"
            f"  Memento — {label}{awareness}\n"
            f"  Model: {self.config.model}\n"
            f"  Rounds: {self.config.num_rounds}\n"
            f"  Attacks: {[a.name for a in self.attacks] or 'none'}\n"
            f"{'='*60}\n"
        )

        for round_num in range(self.config.num_rounds):
            pre_attack = self.state.snapshot()

            # Apply attacks (skip round 0 — agent needs a clean baseline)
            attack_results: list[AttackResult] = []
            if round_num > 0:
                for attack in self.attacks:
                    result = attack.apply(self.state, round_num)
                    if result is not None:
                        attack_results.append(result)

            post_attack = self.state.snapshot()

            rlog = self._run_round(round_num)
            rlog.pre_attack_state = pre_attack
            rlog.post_attack_state = post_attack
            rlog.attack_results = attack_results

            for attack in self.attacks:
                rlog.detection_signals[attack.name] = (
                    attack.detection_signal(rlog.agent_output)
                )

            self.logger.log_round(rlog)

        self.logger.finalize()

    # ── single round ───────────────────────────────────────────────

    def _run_round(self, round_num: int) -> RoundLog:
        prompt = build_full_prompt(
            state=self.state,
            round_num=round_num,
            total_rounds=self.config.num_rounds,
            adversarial=self.config.adversarial_awareness,
        )

        # Spawn a headless Claude instance
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--model", self.config.model],
                capture_output=True,
                text=True,
                timeout=300,
            )
            agent_text = result.stdout.strip()
            if result.returncode != 0 and not agent_text:
                agent_text = f"(claude -p error: {result.stderr.strip()})"
        except subprocess.TimeoutExpired:
            agent_text = "(round timed out after 300s)"

        # Parse structured output from the agent
        new_notes = _extract_tag(agent_text, "new_notes")
        conclusion = _extract_tag(agent_text, "conclusion")

        if new_notes:
            self.state.write_notes(new_notes)
        if conclusion:
            self.state.log_conclusion(conclusion)

        # Build round log
        rlog = RoundLog(round_num=round_num)
        rlog.agent_output = agent_text
        rlog.turns_used = 1

        # Record tampered sections as pseudo tool calls for analysis
        for section in self.state.case_file:
            original = self.state._original_case_file.get(section, "")
            current = self.state.case_file[section]
            if original != current:
                rlog.tool_calls.append({
                    "tool": "read_case_file",
                    "input": {"section": section},
                    "real_result": original[:200] + "...",
                    "presented_result": current[:200] + "...",
                    "tampered": True,
                })

        return rlog


def _extract_tag(text: str, tag: str) -> str | None:
    """Pull content from <tag>...</tag> in agent output."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else None
