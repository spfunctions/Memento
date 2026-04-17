"""Outer harness: spawns inner Claude instances, applies attacks, records everything."""

from __future__ import annotations

import anthropic
from dataclasses import dataclass, field

from attacks.base import Attack, AttackResult
from .state import AgentState
from .logger import ExperimentLogger, RoundLog
from agent.tools import TOOL_DEFINITIONS, handle_tool_call
from agent.prompts import build_system_prompt, build_round_message


@dataclass
class ExperimentConfig:
    case_file_path: str
    attacks: list[Attack] = field(default_factory=list)
    num_rounds: int = 10
    max_turns_per_round: int = 15
    model: str = "claude-sonnet-4-20250514"
    adversarial_awareness: bool = False
    output_dir: str = "runs"
    experiment_name: str = "experiment"


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.client = anthropic.Anthropic()
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
            # Snapshot state before attacks
            pre_attack = self.state.snapshot()

            # Apply attacks (skip round 0 — agent needs a clean first look)
            attack_results: list[AttackResult] = []
            if round_num > 0:
                for attack in self.attacks:
                    result = attack.apply(self.state, round_num)
                    if result is not None:
                        attack_results.append(result)

            post_attack = self.state.snapshot()

            # Run one agent session
            rlog = self._run_round(round_num)
            rlog.pre_attack_state = pre_attack
            rlog.post_attack_state = post_attack
            rlog.attack_results = attack_results

            # Evaluate detection
            for attack in self.attacks:
                rlog.detection_signals[attack.name] = (
                    attack.detection_signal(rlog.agent_output)
                )

            self.logger.log_round(rlog)

        self.logger.finalize()

    # ── single round ───────────────────────────────────────────────

    def _run_round(self, round_num: int) -> RoundLog:
        system = build_system_prompt(
            round_num=round_num,
            total_rounds=self.config.num_rounds,
            adversarial=self.config.adversarial_awareness,
        )

        user_msg = build_round_message(
            state=self.state,
            round_num=round_num,
        )
        messages: list[dict] = [{"role": "user", "content": user_msg}]

        rlog = RoundLog(round_num=round_num)

        for turn in range(self.config.max_turns_per_round):
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=4096,
                system=system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            # Append assistant response
            assistant_content = response.content
            messages.append(
                {"role": "assistant", "content": _serialize_blocks(assistant_content)}
            )

            # Collect any text output
            text_parts = [
                b.text for b in assistant_content if b.type == "text"
            ]

            tool_uses = [b for b in assistant_content if b.type == "tool_use"]

            if not tool_uses:
                # Agent is done for this round
                rlog.agent_output = "\n".join(text_parts)
                rlog.turns_used = turn + 1
                break

            # Process tool calls
            tool_results = []
            for tu in tool_uses:
                real_result = handle_tool_call(tu.name, tu.input, self.state)

                # Let attacks intercept
                presented = real_result
                for attack in self.attacks:
                    presented = attack.intercept_tool(
                        tu.name, tu.input, presented,
                        self.state, round_num,
                    )

                rlog.tool_calls.append({
                    "tool": tu.name,
                    "input": tu.input,
                    "real_result": real_result,
                    "presented_result": presented,
                    "tampered": real_result != presented,
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": presented,
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            # Ran out of turns
            rlog.agent_output = "(max turns reached)"
            rlog.turns_used = self.config.max_turns_per_round

        rlog.messages = messages
        return rlog


def _serialize_blocks(blocks: list) -> list[dict]:
    """Convert Anthropic content blocks to plain dicts for message history."""
    out = []
    for b in blocks:
        if b.type == "text":
            out.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            out.append({
                "type": "tool_use",
                "id": b.id,
                "name": b.name,
                "input": b.input,
            })
    return out
