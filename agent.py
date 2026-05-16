"""
Eterna Trading Agent — main entry point.

Uses Claude (claude-opus-4-7) with adaptive thinking as the decision-making brain.
Executes trades via the Eterna MCP server through execute_code calls.
"""

from __future__ import annotations

import json
import sys
import anthropic

import config
from eterna_mcp import EternaMCPClient
from tools import TOOL_DEFINITIONS, dispatch_tool

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert algorithmic trading agent for cryptocurrency perpetual futures \
on the Eterna exchange.

Your goal is to {objective}.

## Core Trading Guidelines

- **Check before trading**: Always call get_account_status first to know your balance \
and open positions.
- **Position sizing**: Never risk more than {max_risk_pct}% of available balance per trade. \
Calculate position size based on the distance to your stop-loss.
- **Stop-losses are mandatory**: Every new position must have a stop-loss set at order \
placement time. No exceptions.
- **Leverage discipline**: Default to {default_leverage}x leverage. Never exceed \
{max_leverage}x. Lower leverage for volatile markets.
- **Confirm signals**: Before entering a trade, gather at least 2-3 confirming signals \
from different indicators (e.g., RSI + MACD trend + EMA alignment).
- **Monitor positions**: Regularly review open positions. Move stop-losses to break-even \
once a position is 1% in profit.
- **Risk/reward**: Only enter trades with a minimum 2:1 reward-to-risk ratio.

## Market Analysis Approach

1. Identify trending symbols from market data (high volume, strong momentum).
2. Check RSI (oversold <30 for long, overbought >70 for short).
3. Confirm trend direction with MACD (signal line cross).
4. Use EMA/SMA for trend alignment (price above EMA = bullish).
5. Bollinger Bands for volatility and breakout detection.
6. Check funding rate — avoid longs when funding is very high (>0.1%).

## Order Execution Rules

- Use Market orders for entries in trending markets.
- Use Limit orders near support/resistance for better fills.
- Close positions partially at first target, move stop to break-even.
- When in doubt, do not trade. Capital preservation is priority #1.

## Preferred Symbols

{preferred_symbols}

Always explain your reasoning before executing any trade.\
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(
        objective=config.TRADING_OBJECTIVE,
        max_risk_pct=config.MAX_RISK_PCT,
        default_leverage=config.DEFAULT_LEVERAGE,
        max_leverage=config.MAX_LEVERAGE,
        preferred_symbols=", ".join(config.PREFERRED_SYMBOLS),
    )


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_agent(user_message: str, verbose: bool = True) -> str:
    """
    Run a single agent session: send user_message, let Claude use tools
    until it reaches end_turn, and return the final text response.
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    messages: list[dict] = [{"role": "user", "content": user_message}]
    system = build_system_prompt()

    with EternaMCPClient(config.ETERNA_MCP_URL, config.ETERNA_API_KEY) as mcp:
        for round_num in range(config.MAX_TOOL_ROUNDS):
            if verbose:
                print(f"\n[Round {round_num + 1}] Calling Claude...", flush=True)

            # Stream the response
            with client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=8096,
                thinking={"type": "adaptive"},
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ) as stream:
                response = stream.get_final_message()

            if verbose:
                _print_response(response)

            # Add assistant turn to history
            messages.append({"role": "assistant", "content": response.content})

            stop_reason = response.stop_reason

            if stop_reason == "end_turn":
                # Extract final text
                return _extract_text(response)

            if stop_reason in ("tool_use", "pause_turn"):
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input

                    if verbose:
                        print(f"  -> Tool: {tool_name}({json.dumps(tool_input, indent=2)})", flush=True)

                    try:
                        result = dispatch_tool(mcp, tool_name, tool_input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(result, default=str),
                            }
                        )
                        if verbose:
                            print(f"  <- {json.dumps(result, default=str)[:300]}", flush=True)
                    except Exception as exc:
                        error_msg = str(exc)
                        if verbose:
                            print(f"  <- ERROR: {error_msg}", flush=True)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({"error": error_msg}),
                                "is_error": True,
                            }
                        )

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                continue

            # Unexpected stop reason
            break

    return _extract_text(response)


def _extract_text(response) -> str:
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _print_response(response) -> None:
    for block in response.content:
        if hasattr(block, "text"):
            print(f"\n[Claude]: {block.text}", flush=True)
        elif block.type == "thinking":
            pass  # thinking content omitted by default on Opus 4.7
        elif block.type == "tool_use":
            pass  # printed in the tool dispatch section


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Eterna Trading Agent")
    parser.add_argument(
        "instruction",
        nargs="?",
        default=(
            "Analyze the current market conditions for the preferred symbols, "
            "identify the best trading opportunity, and execute a trade if conditions are favorable. "
            "Start by checking account status."
        ),
        help="Trading instruction for the agent",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress tool call output")
    args = parser.parse_args()

    print("=" * 60)
    print("Eterna Trading Agent")
    print("=" * 60)
    print(f"Instruction: {args.instruction}\n")

    result = run_agent(args.instruction, verbose=not args.quiet)

    print("\n" + "=" * 60)
    print("Final response:")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
